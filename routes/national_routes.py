
from flask import Blueprint, request, jsonify
from firebase_config import get_firestore_db
from google.cloud.firestore_v1.base_query import FieldFilter
from firebase_admin import firestore
from national_system_logs_storage import list_national_system_logs

bp = Blueprint('national', __name__, url_prefix='/national')

@bp.route('/operations/projects/api/<project_id>/delete', methods=['DELETE'])
def delete_project_national(project_id):
    db = get_firestore_db()
    try:
        db.collection('projects').document(project_id).delete()
        return jsonify({'success': True, 'message': 'Project deleted.'})
    except Exception as e:
        print(f"[ERROR] Failed to delete project: {e}")
        return jsonify({'success': False, 'error': 'Failed to delete project.'}), 500
from flask import Blueprint, render_template, jsonify, session
from firebase_config import get_firestore_db
from datetime import datetime
from firebase_auth_middleware import role_required
from entities_storage import list_entities


bp = Blueprint('national', __name__, url_prefix='/national')

# -----------------------------
# APPLICATIONS (National)
# -----------------------------
@bp.route('/application-national')
@role_required('national', 'national_admin')
def application_national_view():

    try:
        db = get_firestore_db()

        apps_ref = db.collection('applications')
        docs = apps_ref.stream()

        applications = []
        total_count = 0
        approved_count = 0
        pending_count = 0
        rejected_count = 0
        forwarded_count = 0

        from collections import defaultdict
        monthly_trend = defaultdict(int)
        region_count = defaultdict(int)
        status_breakdown = defaultdict(int)

        for doc in docs:
            data = doc.to_dict()

            status = (data.get('status', 'pending') or 'pending').lower()

            # National sees approved AND to review from Regional
            if status in ['approved', 'to review', 'review']:
                total_count += 1

                national_status = (data.get('nationalStatus', 'pending') or 'pending').lower()
                if national_status == 'approved':
                    approved_count += 1
                elif national_status == 'rejected':
                    rejected_count += 1
                else:
                    pending_count += 1

                if national_status in ['approved', 'rejected']:
                    status_breakdown[national_status] += 1
                else:
                    status_breakdown['pending'] += 1

                created_at = data.get('createdAt') or data.get('dateFiled') or data.get('date_filed')
                date_obj = None

                if created_at:
                    if isinstance(created_at, str):
                        try:
                            date_obj = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                            date_filed = date_obj.strftime('%b %d, %Y')
                        except Exception:
                            date_filed = created_at
                    elif hasattr(created_at, 'strftime'):
                        date_obj = created_at
                        date_filed = created_at.strftime('%b %d, %Y')
                    else:
                        date_filed = 'N/A'
                else:
                    date_filed = 'N/A'

                if date_obj:
                    month_key = date_obj.strftime('%Y-%m')
                    monthly_trend[month_key] += 1

                # Extract applicant fields
                applicant_name = data.get('applicantName') or data.get('fullName') or data.get('name') or 'N/A'
                category = data.get('category') or data.get('applicantCategory') or 'N/A'
                region = data.get('region') or 'N/A'
                municipality = data.get('municipality') or 'N/A'
                location = data.get('location') or f"{region} / {municipality}"

                if region and region != 'N/A':
                    region_count[region] += 1

                applications.append({
                    'id': doc.id,
                    'date_filed': date_filed,
                    'reference_id': doc.id[:12].upper(),
                    'applicant_name': applicant_name,
                    'category': category,
                    'location': location,
                    'status': national_status,
                    'regional_status': status
                })

        # Sort by most recent first (string dates sort imperfectly, but acceptable)
        applications.sort(key=lambda x: x['date_filed'], reverse=True)

        # Chart: last 6 months
        import calendar
        current_date = datetime.now()
        last_6_months = []
        trend_data = []

        for i in range(5, -1, -1):
            target_month = current_date.month - i
            target_year = current_date.year
            while target_month <= 0:
                target_month += 12
                target_year -= 1

            month_key = f"{target_year}-{target_month:02d}"
            month_label = calendar.month_abbr[target_month]
            last_6_months.append(month_label)
            trend_data.append(monthly_trend.get(month_key, 0))

        # Top 5 regions
        top_regions = sorted(region_count.items(), key=lambda x: x[1], reverse=True)[:5]
        region_labels = [item[0] for item in top_regions] if top_regions else ['N/A']
        region_counts = [item[1] for item in top_regions] if top_regions else [0]

        # Status breakdown
        status_labels = ['Approved', 'Pending', 'Rejected']
        status_data = [
            status_breakdown.get('approved', 0),
            status_breakdown.get('pending', 0),
            status_breakdown.get('rejected', 0),
        ]

        return render_template(
            'national/operations/applications-national.html',
            applications=applications,
            total_count=total_count,
            approved_count=approved_count,
            pending_count=pending_count,
            rejected_count=rejected_count,
            forwarded_count=forwarded_count,
            trend_labels=last_6_months,
            trend_data=trend_data,
            region_labels=region_labels,
            region_counts=region_counts,
            status_labels=status_labels,
            status_data=status_data
        )

    except Exception as e:
        print(f"Error fetching applications: {str(e)}")
        import traceback
        traceback.print_exc()

        return render_template(
            'national/applications-national.html',
            applications=[],
            total_count=0,
            approved_count=0,
            pending_count=0,
            rejected_count=0,
            forwarded_count=0,
            trend_labels=['S', 'O', 'N', 'D', 'J', 'F'],
            trend_data=[0, 0, 0, 0, 0, 0],
            region_labels=['N/A'],
            region_counts=[0],
            status_labels=['Approved', 'Pending', 'Rejected'],
            status_data=[0, 0, 0]
        )


# View individual application
@bp.route('/application-view/<application_id>')
@role_required('national', 'national_admin')
def application_view_national(application_id):
    return render_template('national/operations/application-national-view.html')


# -----------------------------
# PERMITS (National)
# -----------------------------
@bp.route('/permit-national')
@role_required('national', 'national_admin')
def permit_national_view():
    try:
        db = get_firestore_db()

        permits_ref = db.collection('license_applications')
        docs = permits_ref.stream()

        permits = []
        total_count = 0
        approved_count = 0
        pending_count = 0
        rejected_count = 0

        from collections import defaultdict
        monthly_trend = defaultdict(int)
        region_count = defaultdict(int)
        status_breakdown = defaultdict(int)

        for doc in docs:
            data = doc.to_dict()

            status = (data.get('status', 'pending') or 'pending').lower()
            national_status = (data.get('nationalStatus', 'pending') or 'pending').lower()
            regional_status = (data.get('regionalStatus', '') or '').lower()
            forwarded_to_level = str(data.get('forwardedToLevel') or '').strip().lower()

            is_forwarded_to_national = (
                forwarded_to_level == 'national'
                or status.startswith('forwarded')
                or status in {'forwarded-to-national', 'to-review', 'to review', 'review'}
                or national_status in {'pending', 'approved', 'rejected', 'cancelled', 'canceled'}
            )

            if is_forwarded_to_national:
                total_count += 1

                if national_status == 'approved':
                    approved_count += 1
                elif national_status == 'rejected':
                    rejected_count += 1
                elif national_status in ['cancelled', 'canceled']:
                    rejected_count += 1
                else:
                    pending_count += 1

                if national_status in ['approved', 'rejected']:
                    status_breakdown[national_status] += 1
                elif national_status in ['cancelled', 'canceled']:
                    status_breakdown['rejected'] += 1
                else:
                    status_breakdown['pending'] += 1

                created_at = data.get('createdAt')
                date_obj = None
                if created_at:
                    if isinstance(created_at, str):
                        try:
                            date_obj = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                            date_filed = date_obj.strftime('%b %d, %Y')
                        except Exception:
                            date_filed = created_at
                    elif hasattr(created_at, 'strftime'):
                        date_obj = created_at
                        date_filed = created_at.strftime('%b %d, %Y')
                    else:
                        date_filed = 'N/A'
                else:
                    date_filed = 'N/A'

                if date_obj:
                    month_key = date_obj.strftime('%Y-%m')
                    monthly_trend[month_key] += 1

                form_data = data.get('formData', {}) or {}

                full_name = form_data.get('fullName', 'N/A')
                municipality = form_data.get('municipality', 'N/A')
                region = form_data.get('region', 'N/A')
                location = f"{region} / {municipality}"

                if region and region != 'N/A':
                    region_count[region] += 1

                app_type = data.get('applicationType', 'N/A')
                classification_map = {
                    'farm-visit': 'Farm Permit',
                    'fishery-permit': 'Fishery License',
                    'livestock': 'Livestock Permit',
                    'forest': 'Forestry Permit',
                    'wildlife': 'Wildlife Permit',
                    'environment': 'ECC Permit'
                }
                classification = classification_map.get(str(app_type).lower(), str(app_type).upper())

                issue_date = data.get('issueDate', '—')
                expiry_date = data.get('expiryDate', '—')

                if national_status == 'approved':
                    status_display = 'Approved by National'
                elif national_status == 'rejected':
                    status_display = 'Rejected by National'
                elif national_status in ['cancelled', 'canceled']:
                    status_display = 'Cancelled'
                elif is_forwarded_to_national:
                    status_display = 'Forwarded to National'
                elif regional_status == 'approved':
                    status_display = 'Approved by Regional'
                elif regional_status == 'rejected':
                    status_display = 'Rejected by Regional'
                else:
                    status_display = 'Pending National Review'

                permits.append({
                    'id': doc.id,
                    'reference_id': doc.id[:12].upper(),
                    'applicant_name': full_name,
                    'classification': classification,
                    'location': location,
                    'region': region,
                    'date_filed': date_filed,
                    'status': status_display,
                    'status_raw': national_status,
                    'regional_status': status,
                    'issue_date': issue_date,
                    'expiry_date': expiry_date,
                    'date_sort': date_obj.timestamp() if date_obj else 0
                })

        permits.sort(key=lambda x: x.get('date_sort', 0), reverse=True)

        import calendar
        current_date = datetime.now()
        last_6_months = []
        trend_data = []

        for i in range(5, -1, -1):
            target_month = current_date.month - i
            target_year = current_date.year
            while target_month <= 0:
                target_month += 12
                target_year -= 1

            month_key = f"{target_year}-{target_month:02d}"
            month_label = calendar.month_abbr[target_month]
            last_6_months.append(month_label)
            trend_data.append(monthly_trend.get(month_key, 0))

        top_regions = sorted(region_count.items(), key=lambda x: x[1], reverse=True)[:5]
        region_labels = [item[0] for item in top_regions] if top_regions else ['N/A']
        region_counts = [item[1] for item in top_regions] if top_regions else [0]

        status_labels = ['Approved', 'Pending', 'Rejected']
        status_data = [
            status_breakdown.get('approved', 0),
            status_breakdown.get('pending', 0),
            status_breakdown.get('rejected', 0)
        ]

        return render_template(
            'national/operations/licensing-permit-national.html',
            permits=permits,
            total_count=total_count,
            approved_count=approved_count,
            pending_count=pending_count,
            rejected_count=rejected_count,
            trend_labels=last_6_months,
            trend_data=trend_data,
            region_labels=region_labels,
            region_counts=region_counts,
            status_labels=status_labels,
            status_data=status_data
        )

    except Exception as e:
        print(f"Error fetching permits: {str(e)}")
        import traceback
        traceback.print_exc()

        return render_template(
            'national/licensing-permit-national.html',
            permits=[],
            total_count=0,
            approved_count=0,
            pending_count=0,
            rejected_count=0,
            trend_labels=['S', 'O', 'N', 'D', 'J', 'F'],
            trend_data=[0, 0, 0, 0, 0, 0],
            region_labels=['N/A'],
            region_counts=[0],
            status_labels=['Approved', 'Pending', 'Rejected'],
            status_data=[0, 0, 0]
        )


@bp.route('/permit-national/action/<permit_id>', methods=['POST'])
@role_required('national', 'national_admin')
def permit_national_action(permit_id):
    """Approve or reject a forwarded permit at national level."""
    try:
        db = get_firestore_db()
        payload = request.get_json(silent=True) or {}
        action = str(payload.get('action') or '').strip().lower()

        if action not in {'approved', 'rejected'}:
            return jsonify({'success': False, 'message': 'Invalid action'}), 400

        doc_ref = db.collection('license_applications').document(permit_id)
        snap = doc_ref.get()
        if not snap.exists:
            return jsonify({'success': False, 'message': 'Permit not found'}), 404

        update_fields = {
            'nationalStatus': action,
            'status': action,
            'updatedAt': datetime.utcnow(),
            'forwardedToLevel': 'National',
            'approvedByLevel': 'National' if action == 'approved' else '',
            'rejectedByLevel': 'National' if action == 'rejected' else '',
        }
        doc_ref.update(update_fields)

        return jsonify({'success': True, 'message': f'Permit {action} successfully'})
    except Exception as e:
        print(f'Error updating permit national action: {e}')
        return jsonify({'success': False, 'message': 'Failed to update permit status'}), 500


# -----------------------------
# SERVICES (National)
# -----------------------------
@bp.route('/service-national')
@role_required('national', 'national_admin')
def service_national_view():
    try:
        db = get_firestore_db()

        service_requests_ref = db.collection('service_requests')
        docs = service_requests_ref.stream()

        service_requests = []
        total_count = 0
        completed_count = 0
        pending_count = 0
        rejected_count = 0

        from collections import defaultdict
        monthly_trend = defaultdict(int)
        service_type_count = defaultdict(int)
        status_breakdown = defaultdict(int)

        for doc in docs:
            data = doc.to_dict()

            status = (data.get('status', 'pending') or 'pending').lower()

            if status in ['approved', 'to review', 'review']:
                total_count += 1

                national_status = (data.get('nationalStatus', 'pending') or 'pending').lower()
                if national_status == 'approved':
                    completed_count += 1
                elif national_status == 'rejected':
                    rejected_count += 1
                else:
                    pending_count += 1

                created_at = data.get('createdAt')
                date_obj = None
                if created_at:
                    if isinstance(created_at, str):
                        try:
                            date_obj = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                            date_filed = date_obj.strftime('%b %d, %Y')
                        except Exception:
                            date_filed = created_at
                    elif hasattr(created_at, 'strftime'):
                        date_obj = created_at
                        date_filed = created_at.strftime('%b %d, %Y')
                    else:
                        date_filed = 'N/A'
                else:
                    date_filed = 'N/A'

                if date_obj:
                    month_key = date_obj.strftime('%Y-%m')
                    monthly_trend[month_key] += 1

                service_type = data.get('serviceType', 'N/A')
                service_type_count[service_type] += 1

                if national_status in ['approved', 'rejected']:
                    status_breakdown[national_status] += 1
                else:
                    status_breakdown['pending'] += 1

                full_name = data.get('fullName', data.get('applicantName', 'N/A'))
                region = data.get('region', 'N/A')
                municipality = data.get('municipality', data.get('location', 'N/A'))
                location = f"{region} / {municipality}"

                approved_by_regional = data.get('approvedByRegional', 'N/A')
                approval_date = data.get('approvalDate', 'N/A')

                service_requests.append({
                    'id': doc.id,
                    'date_filed': date_filed,
                    'reference_id': doc.id[:10].upper(),
                    'applicant_name': full_name,
                    'service_type': service_type,
                    'location': location,
                    'status': national_status,
                    'regional_status': status,
                    'approved_by_regional': approved_by_regional,
                    'approval_date': approval_date
                })

        service_requests.sort(key=lambda x: x['date_filed'], reverse=True)

        import calendar
        current_date = datetime.now()
        last_6_months = []
        trend_data = []

        for i in range(5, -1, -1):
            target_month = current_date.month - i
            target_year = current_date.year
            while target_month <= 0:
                target_month += 12
                target_year -= 1

            month_key = f"{target_year}-{target_month:02d}"
            month_label = calendar.month_abbr[target_month]
            last_6_months.append(month_label)
            trend_data.append(monthly_trend.get(month_key, 0))

        top_service_types = sorted(service_type_count.items(), key=lambda x: x[1], reverse=True)[:5]
        service_labels = [item[0][:10] for item in top_service_types] if top_service_types else ['N/A']
        service_counts = [item[1] for item in top_service_types] if top_service_types else [0]

        status_labels = ['Approved', 'Pending', 'Rejected']
        status_data = [
            status_breakdown.get('approved', 0),
            status_breakdown.get('pending', 0),
            status_breakdown.get('rejected', 0)
        ]

        return render_template(
            'national/service-national.html',
            service_requests=service_requests,
            total_count=total_count,
            completed_count=completed_count,
            pending_count=pending_count,
            rejected_count=rejected_count,
            trend_labels=last_6_months,
            trend_data=trend_data,
            service_labels=service_labels,
            service_counts=service_counts,
            status_labels=status_labels,
            status_data=status_data
        )

    except Exception as e:
        print(f"Error fetching service requests: {str(e)}")
        import traceback
        traceback.print_exc()

        return render_template(
            'national/service-national.html',
            service_requests=[],
            total_count=0,
            completed_count=0,
            pending_count=0,
            rejected_count=0,
            trend_labels=['S', 'O', 'N', 'D', 'J', 'F'],
            trend_data=[0, 0, 0, 0, 0, 0],
            service_labels=['N/A'],
            service_counts=[0],
            status_labels=['Approved', 'Pending', 'Rejected'],
            status_data=[0, 0, 0]
        )


# -----------------------------
# INVENTORY (National)
# -----------------------------
@bp.route('/inventory-national')
@role_required('national', 'national_admin')
def inventory_national_view():
    try:
        db = get_firestore_db()
        from models.region_province_map import region_province_map

        def _clean(value):
            return str(value or '').strip()

        def _region_from_province(province_name):
            prov = _clean(province_name).lower()
            if not prov:
                return ''
            for region_label, provinces in (region_province_map or {}).items():
                for p in provinces or []:
                    if _clean(p).lower() == prov:
                        return region_label
            return ''

        inventory_ref = db.collection('inventory_registrations')
        docs = inventory_ref.stream()

        users_ref = db.collection('users')
        users_map = {u.id: (u.to_dict() or {}) for u in users_ref.stream()}

        inventory_records = []
        total_count = 0

        from collections import defaultdict
        category_count = defaultdict(int)
        region_count = defaultdict(int)

        for doc in docs:
            data = doc.to_dict()
            user_data = users_map.get(data.get('userId', ''), {})
            full_name = (
                f"{user_data.get('firstName', '')} {user_data.get('lastName', '')}".strip()
                or data.get('userEmail', 'N/A')
            )
            municipality = data.get('municipality') or user_data.get('municipality', 'N/A')
            province = (
                data.get('province')
                or user_data.get('province')
                or data.get('province_name')
                or user_data.get('province_name')
                or ''
            )

            region = (
                data.get('region')
                or data.get('regionName')
                or data.get('region_name')
                or user_data.get('regionName')
                or user_data.get('region')
                or user_data.get('region_name')
                or _region_from_province(province)
                or 'N/A'
            )

            sector = str(data.get('sector', '')).lower()
            category_map = {
                'farming': 'Chemical Inventory',
                'fisheries': 'Natural Resources',
                'livestock': 'Biodiversity Inventory',
                'forestry': 'Natural Resources',
                'wildlife': 'Protected Area',
                'environment': 'Natural Resources'
            }
            category = category_map.get(sector, 'Chemical Inventory')
            quantity = data.get('stockAvailable', data.get('quantity', 0))
            try:
                quantity = float(quantity or 0)
            except Exception:
                quantity = 0

            # Use real fetched volume totals for dashboard charts
            category_count[category] += quantity

            if region and region != 'N/A':
                region_count[region] += quantity

            total_count += 1

            description = data.get('resourceName') or data.get('notes') or 'General Inventory'

            main_status = str(data.get('status', 'pending') or 'pending').strip().lower()
            regional_status = str(data.get('regionalStatus', '') or '').strip().lower()
            national_status = str(data.get('nationalStatus', '') or '').strip().lower()
            approved_by_level = str(data.get('approvedByLevel', '') or '').strip().upper()
            rejected_by_level = str(data.get('rejectedByLevel', '') or '').strip().upper()
            forwarded_to_level = str(data.get('forwardedToLevel', '') or '').strip().upper()

            if national_status == 'approved':
                status_display = 'APPROVED BY NATIONAL'
            elif national_status == 'rejected':
                status_display = 'REJECTED BY NATIONAL'
            elif rejected_by_level:
                status_display = f'REJECTED BY {rejected_by_level}'
            elif approved_by_level:
                status_display = f'APPROVED BY {approved_by_level}'
            elif main_status in {'forwarded-to-national', 'forwarded-national'} or forwarded_to_level == 'NATIONAL':
                status_display = 'FORWARDED TO NATIONAL'
            elif main_status in {'to-review', 'to_review'}:
                status_display = 'FORWARDED TO REGIONAL'
            elif regional_status == 'approved':
                status_display = 'APPROVED BY REGIONAL'
            elif regional_status == 'rejected':
                status_display = 'REJECTED BY REGIONAL'
            else:
                status_display = 'PENDING'

            inventory_records.append({
                'id': doc.id,
                'category': category,
                'description': description,
                'quantity': quantity,
                'region': region,
                'municipality': municipality,
                'applicant_name': full_name,
                'status': data.get('status', 'pending'),
                'regionalStatus': data.get('regionalStatus', ''),
                'nationalStatus': data.get('nationalStatus', ''),
                'approvedByLevel': data.get('approvedByLevel', ''),
                'rejectedByLevel': data.get('rejectedByLevel', ''),
                'forwardedToLevel': data.get('forwardedToLevel', ''),
                'registrationFee': data.get('registrationFee', 0),
                'createdAt': data.get('createdAt'),
                'unitOfMeasure': data.get('unitOfMeasure', 'pcs'),
                'status_display': status_display
            })

        chemical_count = category_count.get('Chemical Inventory', 0)
        natural_resources_count = category_count.get('Natural Resources', 0)
        protected_area_count = category_count.get('Protected Area', 0)
        biodiversity_count = category_count.get('Biodiversity Inventory', 0)

        category_labels = ['Chemical', 'Natural Res.', 'Protected', 'Biodiversity']
        category_data = [
            chemical_count,
            natural_resources_count,
            protected_area_count,
            biodiversity_count
        ]

        top_regions = sorted(region_count.items(), key=lambda x: x[1], reverse=True)[:5]
        region_labels = [item[0] for item in top_regions] if top_regions else ['N/A']
        region_data = [item[1] for item in top_regions] if top_regions else [0]

        return render_template(
            'national/logistics/inventory-national.html',
            inventory_records=inventory_records,
            total_count=total_count,
            chemical_count=chemical_count,
            natural_resources_count=natural_resources_count,
            protected_area_count=protected_area_count,
            biodiversity_count=biodiversity_count,
            category_labels=category_labels,
            category_data=category_data,
            region_labels=region_labels,
            region_data=region_data
        )

    except Exception as e:
        print(f"Error fetching inventory: {str(e)}")
        import traceback
        traceback.print_exc()

        return render_template(
            'national/inventory-national.html',
            inventory_records=[],
            total_count=0,
            chemical_count=0,
            natural_resources_count=0,
            protected_area_count=0,
            biodiversity_count=0,
            category_labels=['Chemical', 'Natural Res.', 'Protected', 'Biodiversity'],
            category_data=[0, 0, 0, 0],
            region_labels=['N/A'],
            region_data=[0]
        )


@bp.route('/inventory-national/api/<inventory_id>/status', methods=['POST'])
@role_required('national', 'national_admin')
def update_inventory_national_status(inventory_id):
    """National-level approve/reject endpoint for inventory registrations."""
    try:
        db = get_firestore_db()
        payload = request.get_json(silent=True) or {}
        requested_status = str(payload.get('status') or '').strip().lower()

        if requested_status not in {'approved', 'rejected'}:
            return jsonify({'status': 'error', 'message': 'Invalid action.'}), 400

        inv_ref = db.collection('inventory_registrations').document(inventory_id)
        inv_doc = inv_ref.get()
        if not inv_doc.exists:
            return jsonify({'status': 'error', 'message': 'Inventory record not found.'}), 404

        inv_data = inv_doc.to_dict() or {}
        current_national = str(inv_data.get('nationalStatus') or '').strip().lower()
        if current_national in {'approved', 'rejected'}:
            return jsonify({'status': 'error', 'message': 'National action already finalized for this record.'}), 409

        update_data = {
            'status': requested_status,
            'nationalStatus': requested_status,
            'updatedAt': datetime.utcnow(),
        }

        if requested_status == 'approved':
            update_data.update({
                'approvedByLevel': 'National',
                'approvedAt': datetime.utcnow(),
                'rejectedByLevel': '',
                'rejectedByEmail': ''
            })
        else:
            update_data.update({
                'rejectedByLevel': 'National',
                'rejectedAt': datetime.utcnow(),
                'approvedByLevel': '',
                'approvedByEmail': ''
            })

        inv_ref.update(update_data)
        return jsonify({'status': 'success', 'message': f'Inventory {requested_status} successfully.'}), 200

    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


# -----------------------------
# SIMPLE PAGES (National)
# -----------------------------
@bp.route('/user-inventory-national')
@role_required('national', 'national_admin')
def user_inventory_national_view():
    return render_template('national/user-inventory-national.html')

@bp.route('/user-management-national')
@role_required('national', 'national_admin')
def user_management_national_view():
    return render_template('national/system/user-national.html')

@bp.route('/sales-return')
@role_required('national', 'national_admin')
def sales_return_national_view():
    return render_template('national/logistics/sales-return.html')


@bp.route('/products-national')
@role_required('national', 'national_admin')
def products_national():
    return render_template('national/logistics/products-national.html')


@bp.route('/purchases')
@role_required('national', 'national_admin')
def purchases():
    return render_template('national/logistics/purchases.html')


@bp.route('/sales')
@role_required('national', 'national_admin')
def sales():
    return render_template('national/logistics/sales.html')


@bp.route('/sales-return')
@role_required('national', 'national_admin')
def sales_return():
    return render_template('national/logistics/sales-return.html')


@bp.route('/distributed-products')
@role_required('national', 'national_admin')
def distributed_products():
    return render_template('national/logistics/distributed-products.html')


@bp.route('/damage-products')
@role_required('national', 'national_admin')
def damage_products():
    return render_template('national/logistics/damage-products.html')


@bp.route('/transfer-products')
@role_required('national', 'national_admin')
def transfer_products():
    return render_template('national/logistics/transfer-products.html')



# Unified quotations view for national
@bp.route('/quotation')
@role_required('national', 'national_admin')
def quotation():
    from quotation_storage import get_quotations
    import json
    from collections import Counter
    from quotation_storage import get_all_quotations
    quotations = get_all_quotations()
    def to_float(value):
        try:
            return float(value)
        except Exception:
            return 0.0
    for q in quotations:
        q['amount_value'] = to_float(q.get('amount'))
        q['amount'] = f"{q['amount_value']:,.2f}"
        q['status'] = str(q.get('status') or 'Pending').capitalize()
    total_quotes = len(quotations)
    pending_quotes = len([q for q in quotations if str(q.get('status')).upper() == 'PENDING'])
    cancelled_quotes = len([q for q in quotations if str(q.get('status')).upper() == 'CANCELLED'])
    total_value_number = sum([to_float(q.get('amount_value')) for q in quotations])
    total_value = f"{total_value_number:,.2f}"
    regions = sorted(list({(q.get('region') or '').strip() for q in quotations if (q.get('region') or '').strip()}))
    monthly_amounts = Counter()
    for q in quotations:
        date_raw = str(q.get('date') or '').strip()
        try:
            from datetime import datetime
            dt = datetime.fromisoformat(date_raw)
            monthly_amounts[dt.strftime('%b')] += to_float(q.get('amount_value'))
        except Exception:
            continue
    ordered_months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    trend_labels = [m for m in ordered_months if monthly_amounts.get(m)]
    trend_values = [round(monthly_amounts[m], 2) for m in trend_labels]
    if not trend_labels:
        trend_labels = ['No Data']
        trend_values = [0]
    # Import province/municipality mapping for dropdowns
    from models.ph_locations import philippineLocations
    from models.region_province_map import region_province_map
    # province_muni_map is just philippineLocations
    province_muni_map = philippineLocations
    # Always provide status_data for chart (Pending, In Transit, For Delivery, Delivered, Cancelled)
    status_data = [
        len([q for q in quotations if str(q.get('status', '')).lower() == 'pending']),
        len([q for q in quotations if str(q.get('status', '')).lower() == 'in-transit']),
        len([q for q in quotations if str(q.get('status', '')).lower() == 'for-delivery']),
        len([q for q in quotations if str(q.get('status', '')).lower() == 'delivered']),
        len([q for q in quotations if str(q.get('status', '')).lower() == 'cancelled'])
    ]
    return render_template(
        'national/operations/quotation.html',
        quotations=quotations,
        total_quotes=total_quotes,
        pending_quotes=pending_quotes,
        cancelled_quotes=cancelled_quotes,
        total_value=total_value,
        region_province_map=region_province_map,
        province_muni_map=province_muni_map,
        trend_labels_json=json.dumps(trend_labels),
        trend_values_json=json.dumps(trend_values),
        status_data=status_data
    )


@bp.route('/projects')
@role_required('national', 'national_admin')
def projects():
    try:
        import projects_storage
        projects = projects_storage.get_projects_national()
        return render_template(
            'national/operations/projects.html',
            projects=projects,
            user_email=session.get('user_email', 'Unknown')
        )
    except Exception as e:
        print(f"[ERROR] Loading national projects: {e}")
        return render_template('national/operations/projects.html', projects=[], user_email=session.get('user_email', 'Unknown'))


@bp.route('/tasks')
@role_required('national', 'national_admin')
def tasks():
    return render_template('national/operations/tasks.html')


@bp.route('/applicants')
@role_required('national', 'national_admin')
def applicants():
    return render_template('national/HRM/applicants.html')


# -----------------------------
# ACCOUNTING MODULE (National)
# -----------------------------
@bp.route('/accounting/dashboard')
@role_required('national', 'national_admin')
def accounting_dashboard():
    return render_template('national/accounting/accounting-dashboard.html')


@bp.route('/api/entities', methods=['GET'])
@role_required('national', 'national_admin')
def api_get_national_entities():
    """Fetch all entities from regional and municipal levels for national dashboard"""
    try:
        db = get_firestore_db()
        
        # Get all entities from all municipalities and regions
        entities_ref = db.collection("entities")
        docs = entities_ref.stream()
        
        entities = []
        for doc in docs:
            entity = doc.to_dict()
            if entity:
                entities.append(entity)
        
        # Calculate stats - include all entities regardless of level
        active_count = sum(1 for e in entities if e.get('status', '').lower() in ['active', 'enabled'])
        total_count = len(entities)
        
        # Group by type
        by_type = {}
        by_municipality = {}
        
        for e in entities:
            entity_type = e.get('type', 'Unknown')
            municipality = e.get('municipality', 'Regional')
            
            # Count by type
            if entity_type not in by_type:
                by_type[entity_type] = 0
            by_type[entity_type] += 1
            
            # Count by municipality
            if municipality not in by_municipality:
                by_municipality[municipality] = {'count': 0, 'active': 0}
            by_municipality[municipality]['count'] += 1
            if e.get('status', '').lower() in ['active', 'enabled']:
                by_municipality[municipality]['active'] += 1
        
        return jsonify({
            'success': True,
            'entities': entities,
            'stats': {
                'total_entities': total_count,
                'active_entities': active_count,
                'by_type': by_type,
                'by_municipality': by_municipality
            }
        })
    except Exception as e:
        print(f'[ERROR] Failed to fetch national entities: {e}')
        return jsonify({'success': False, 'error': str(e)}), 500


@bp.route('/api/deposits', methods=['GET'])
@role_required('national', 'national_admin')
def api_get_national_deposits():
    """Fetch all deposits from transactions, applications, and service_requests across all municipalities/regions"""
    try:
        db = get_firestore_db()
        total_deposits = 0.0
        deposits_by_type = {'transactions': 0, 'applications': 0, 'service_requests': 0}
        deposit_records = []
        
        # Helper to check if status indicates paid
        paid_markers = {'paid', 'completed', 'settled', 'approved', 'success', 'succeeded'}
        
        def is_paid(status_value):
            return str(status_value or '').strip().lower() in paid_markers
        
        # 1. Get paid transactions
        try:
            trans_ref = db.collection('transactions')
            trans_docs = trans_ref.stream()
            for doc in trans_docs:
                trans = doc.to_dict()
                if trans:
                    # Check status in multiple field name variations
                    status = trans.get('status') or trans.get('paymentStatus') or trans.get('payment_status') or ''
                    amount = float(trans.get('amount', 0) or 0)
                    
                    # Check if either status indicates paid OR payment_method is present + status not failed
                    paid_by_status = is_paid(status)
                    paid_by_method = bool(trans.get('payment_method')) and status.lower() not in {'pending', 'failed', 'expired', 'cancelled'}
                    
                    if amount > 0 and (paid_by_status or paid_by_method):
                        total_deposits += amount
                        deposits_by_type['transactions'] += amount
                        deposit_records.append({
                            'id': doc.id,
                            'source': 'transactions',
                            'amount': amount,
                            'description': trans.get('description', trans.get('name', 'Transaction')),
                            'date': trans.get('paid_at', trans.get('created_at')),
                            'municipality': trans.get('municipality', 'N/A')
                        })
        except Exception as e:
            print(f'[WARN] Error fetching transactions: {e}')
        
        # 2. Get paid applications
        try:
            app_ref = db.collection('applications')
            app_docs = app_ref.stream()
            for doc in app_docs:
                app = doc.to_dict()
                if app:
                    status = app.get('paymentStatus') or app.get('payment_status') or app.get('status') or ''
                    amount = float(app.get('amount', 0) or 0)
                    
                    if amount > 0 and (is_paid(status) or (bool(app.get('payment_method')) and status.lower() not in {'pending', 'failed', 'expired', 'cancelled'})):
                        total_deposits += amount
                        deposits_by_type['applications'] += amount
                        deposit_records.append({
                            'id': doc.id,
                            'source': 'applications',
                            'amount': amount,
                            'description': app.get('application_type', 'Application'),
                            'date': app.get('paid_at', app.get('created_at')),
                            'municipality': app.get('municipality', 'N/A')
                        })
        except Exception as e:
            print(f'[WARN] Error fetching applications: {e}')
        
        # 3. Get paid service requests
        try:
            sr_ref = db.collection('service_requests')
            sr_docs = sr_ref.stream()
            for doc in sr_docs:
                sr = doc.to_dict()
                if sr:
                    status = sr.get('paymentStatus') or sr.get('payment_status') or sr.get('status') or ''
                    amount = float(sr.get('service_fee', 0) or 0)
                    
                    if amount > 0 and (is_paid(status) or (bool(sr.get('payment_method')) and status.lower() not in {'pending', 'failed', 'expired', 'cancelled'})):
                        total_deposits += amount
                        deposits_by_type['service_requests'] += amount
                        deposit_records.append({
                            'id': doc.id,
                            'source': 'service_requests',
                            'amount': amount,
                            'description': sr.get('service_type', 'Service Request'),
                            'date': sr.get('paid_at', sr.get('created_at')),
                            'municipality': sr.get('municipality', 'N/A')
                        })
        except Exception as e:
            print(f'[WARN] Error fetching service_requests: {e}')
        
        return jsonify({
            'success': True,
            'total_deposits': round(total_deposits, 2),
            'by_type': deposits_by_type,
            'records': deposit_records,
            'record_count': len(deposit_records)
        })
    except Exception as e:
        print(f'[ERROR] Failed to fetch national deposits: {e}')
        return jsonify({'success': False, 'error': str(e)}), 500


@bp.route('/api/expenses', methods=['GET'])
@role_required('national', 'national_admin')
def api_get_national_expenses():
    """Fetch all expenses (fund transfers) from national to regions and municipalities"""
    try:
        db = get_firestore_db()
        total_expenses = 0.0
        expense_records = []
        
        # 1. Fetch regional fund distributions (national → regions)
        try:
            fund_ref = db.collection('regional_fund_distribution')
            docs = fund_ref.stream()
            for doc in docs:
                fund = doc.to_dict()
                if fund:
                    amount = float(fund.get('amount', 0) or 0)
                    if amount > 0:
                        total_expenses += amount
                        expense_records.append({
                            'id': doc.id,
                            'type': 'regional_distribution',
                            'amount': amount,
                            'description': fund.get('fund_type', 'Regional Fund Transfer'),
                            'recipient': fund.get('region', 'N/A'),
                            'date': fund.get('date', fund.get('created_at')),
                            'status': fund.get('status', 'completed')
                        })
        except Exception as e:
            print(f'[WARN] Error fetching regional_fund_distribution: {e}')
        
        # 2. Fetch municipal fund distributions (regions/national → municipalities)
        try:
            fund_ref = db.collection('municipal_fund_distribution')
            docs = fund_ref.stream()
            for doc in docs:
                fund = doc.to_dict()
                if fund:
                    amount = float(fund.get('amount', 0) or 0)
                    if amount > 0:
                        total_expenses += amount
                        expense_records.append({
                            'id': doc.id,
                            'type': 'municipal_distribution',
                            'amount': amount,
                            'description': fund.get('fund_type', 'Municipal Fund Transfer'),
                            'recipient': fund.get('municipality', 'N/A'),
                            'date': fund.get('timestamp', fund.get('created_at')),
                            'status': fund.get('status', 'completed')
                        })
        except Exception as e:
            print(f'[WARN] Error fetching municipal_fund_distribution: {e}')
        
        return jsonify({
            'success': True,
            'total_expenses': round(total_expenses, 2),
            'records': expense_records,
            'record_count': len(expense_records)
        })
    except Exception as e:
        print(f'[ERROR] Failed to fetch national expenses: {e}')
        return jsonify({'success': False, 'error': str(e)}), 500


@bp.route('/api/growth-rate', methods=['GET'])
@role_required('national', 'national_admin')
def api_get_national_growth_rate():
    """Calculate growth rate: (current deposits - previous period deposits) / previous period deposits * 100"""
    try:
        db = get_firestore_db()
        from datetime import datetime, timedelta
        
        # Define periods (e.g., current month and previous month)
        today = datetime.now()
        current_month_start = datetime(today.year, today.month, 1)
        if today.month == 1:
            prev_month_start = datetime(today.year - 1, 12, 1)
            prev_month_end = datetime(today.year - 1, 12, 31)
        else:
            prev_month_start = datetime(today.year, today.month - 1, 1)
            prev_month_end = datetime(today.year, today.month - 1 if today.month > 1 else 12, 
                                     28 if today.month - 1 == 2 else (30 if today.month - 1 in [4,6,9,11] else 31))
        
        # Helper to check if status indicates paid
        paid_markers = {'paid', 'completed', 'settled', 'approved', 'success', 'succeeded'}
        
        def is_paid(status_value):
            return str(status_value or '').strip().lower() in paid_markers
        
        def get_deposits_for_period(period_start, period_end):
            """Sum deposits within period"""
            total = 0.0
            try:
                # Check transactions
                trans_docs = db.collection('transactions').stream()
                for doc in trans_docs:
                    trans = doc.to_dict()
                    if trans:
                        status = trans.get('status') or trans.get('paymentStatus') or trans.get('payment_status') or ''
                        amount = float(trans.get('amount', 0) or 0)
                        
                        # Get transaction date
                        tx_date = None
                        paid_at = trans.get('paid_at')
                        if paid_at:
                            if hasattr(paid_at, 'timestamp'):
                                tx_date = datetime.fromtimestamp(paid_at.timestamp())
                            elif isinstance(paid_at, datetime):
                                tx_date = paid_at
                        
                        if tx_date and period_start <= tx_date <= period_end:
                            paid_by_status = is_paid(status)
                            paid_by_method = bool(trans.get('payment_method')) and status.lower() not in {'pending', 'failed', 'expired', 'cancelled'}
                            if amount > 0 and (paid_by_status or paid_by_method):
                                total += amount
            except Exception as e:
                print(f'[WARN] Error in period transactions: {e}')
            
            try:
                # Check applications
                app_docs = db.collection('applications').stream()
                for doc in app_docs:
                    app = doc.to_dict()
                    if app:
                        status = app.get('paymentStatus') or app.get('payment_status') or app.get('status') or ''
                        amount = float(app.get('amount', 0) or 0)
                        
                        # Get application date
                        app_date = None
                        paid_at = app.get('paid_at')
                        if paid_at:
                            if hasattr(paid_at, 'timestamp'):
                                app_date = datetime.fromtimestamp(paid_at.timestamp())
                            elif isinstance(paid_at, datetime):
                                app_date = paid_at
                        
                        if app_date and period_start <= app_date <= period_end:
                            if amount > 0 and (is_paid(status) or (bool(app.get('payment_method')) and status.lower() not in {'pending', 'failed', 'expired', 'cancelled'})):
                                total += amount
            except Exception as e:
                print(f'[WARN] Error in period applications: {e}')
            
            try:
                # Check service requests
                sr_docs = db.collection('service_requests').stream()
                for doc in sr_docs:
                    sr = doc.to_dict()
                    if sr:
                        status = sr.get('paymentStatus') or sr.get('payment_status') or sr.get('status') or ''
                        amount = float(sr.get('service_fee', 0) or 0)
                        
                        # Get service request date
                        sr_date = None
                        paid_at = sr.get('paid_at')
                        if paid_at:
                            if hasattr(paid_at, 'timestamp'):
                                sr_date = datetime.fromtimestamp(paid_at.timestamp())
                            elif isinstance(paid_at, datetime):
                                sr_date = paid_at
                        
                        if sr_date and period_start <= sr_date <= period_end:
                            if amount > 0 and (is_paid(status) or (bool(sr.get('payment_method')) and status.lower() not in {'pending', 'failed', 'expired', 'cancelled'})):
                                total += amount
            except Exception as e:
                print(f'[WARN] Error in period service requests: {e}')
            
            return total
        
        # Get current and previous period deposits
        current_deposits = get_deposits_for_period(current_month_start, today)
        previous_deposits = get_deposits_for_period(prev_month_start, prev_month_end)
        
        # Calculate growth rate
        growth_rate = 0.0
        if previous_deposits > 0:
            growth_rate = ((current_deposits - previous_deposits) / previous_deposits) * 100
        
        return jsonify({
            'success': True,
            'growth_rate': round(growth_rate, 2),
            'current_period': current_deposits,
            'previous_period': previous_deposits,
            'growth_percentage': f"{'+' if growth_rate >= 0 else ''}{round(growth_rate, 2)}%"
        })
    except Exception as e:
        print(f'[ERROR] Failed to calculate growth rate: {e}')
        return jsonify({'success': False, 'error': str(e)}), 500


@bp.route('/api/entities-management', methods=['GET'])
@role_required('national', 'national_admin')
def api_get_entities_management():
    """Fetch all entities (regional and municipal) for management"""
    try:
        db = get_firestore_db()
        entities_data = []

        docs = db.collection('entities').stream()
        for doc in docs:
            entity = doc.to_dict() or {}
            raw_level = str(entity.get('entity_level') or entity.get('level') or '').strip().lower()
            name = entity.get('entity_name') or entity.get('name') or entity.get('office_name') or 'N/A'
            region_name = entity.get('region_name') or entity.get('region') or ''
            municipality_name = entity.get('municipality_name') or entity.get('municipality') or ''

            if raw_level in ('regional', 'region'):
                normalized_level = 'Regional'
            elif raw_level in ('municipal', 'municipality', 'city'):
                normalized_level = 'Municipal'
            else:
                normalized_level = 'Municipal' if municipality_name else 'Regional'

            entities_data.append({
                'id': doc.id,
                'name': name,
                'level': normalized_level,
                'parent_region': region_name or ('—' if normalized_level == 'Regional' else 'N/A'),
                'bank_account': entity.get('bank_account_number') or entity.get('bank_account') or 'N/A',
                'status': entity.get('status') or 'Unknown',
                'municipality': municipality_name or 'N/A'
            })

        # Fallback: if no records exist in entities collection, derive from municipal_offices
        if not entities_data:
            municipal_docs = db.collection('municipal_offices').stream()
            seen_regions = set()
            for doc in municipal_docs:
                office = doc.to_dict() or {}
                municipality_name = office.get('municipality_name') or office.get('municipality') or office.get('name')
                region_name = office.get('region_name') or office.get('region') or 'Unknown Region'
                status = office.get('status') or ('Active' if office.get('is_active') is True else 'Unknown')

                if municipality_name:
                    entities_data.append({
                        'id': doc.id,
                        'name': municipality_name,
                        'level': 'Municipal',
                        'parent_region': region_name,
                        'bank_account': office.get('bank_account_number') or office.get('bank_account') or 'N/A',
                        'status': status,
                        'municipality': municipality_name
                    })

                if region_name and region_name not in seen_regions:
                    seen_regions.add(region_name)

            # Add synthetic regional entries for management visibility
            for region_name in sorted(seen_regions):
                region_id = f"region_{str(region_name).lower().replace(' ', '_').replace('-', '_')}"
                entities_data.append({
                    'id': region_id,
                    'name': region_name,
                    'level': 'Regional',
                    'parent_region': '—',
                    'bank_account': 'N/A',
                    'status': 'Active',
                    'municipality': 'N/A'
                })

        entities_data.sort(key=lambda x: (x.get('parent_region', ''), x.get('name', '')))

        regional_count = sum(1 for e in entities_data if e.get('level') == 'Regional')
        municipal_count = sum(1 for e in entities_data if e.get('level') == 'Municipal')
        active_count = sum(
            1 for e in entities_data
            if str(e.get('status', '')).strip().lower() in ['active', 'enabled', 'approved']
        )

        status_dist = {}
        for e in entities_data:
            status = str(e.get('status') or 'Unknown').strip() or 'Unknown'
            status_dist[status] = status_dist.get(status, 0) + 1

        return jsonify({
            'success': True,
            'entities': entities_data,
            'stats': {
                'regional_count': regional_count,
                'municipal_count': municipal_count,
                'total_count': len(entities_data),
                'active_count': active_count,
                'status_distribution': status_dist
            }
        })
    except Exception as e:
        print(f'[ERROR] Failed to fetch entities for management: {e}')
        return jsonify({'success': False, 'error': str(e)}), 500


@bp.route('/api/entities-management', methods=['PUT'])
@role_required('national', 'national_admin')
def api_update_entity():
    """Update entity details"""
    try:
        from flask import request
        db = get_firestore_db()
        data = request.get_json() or {}

        entity_id = data.get('id')
        if not entity_id:
            return jsonify({'success': False, 'error': 'Entity ID required'}), 400

        update_data = {
            'entity_name': data.get('name', ''),
            'bank_account_number': data.get('bank_account', ''),
            'status': data.get('status', 'active'),
            'updated_at': datetime.now()
        }

        db.collection('entities').document(entity_id).update(update_data)
        return jsonify({'success': True, 'message': 'Entity updated successfully'})
    except Exception as e:
        print(f'[ERROR] Failed to update entity: {e}')
        return jsonify({'success': False, 'error': str(e)}), 500


@bp.route('/api/entities-management', methods=['POST'])
@role_required('national', 'national_admin')
def api_create_entity():
    """Create new entity"""
    try:
        from flask import request
        db = get_firestore_db()
        data = request.get_json() or {}
        level = str(data.get('level') or '').strip().lower()

        normalized_level = 'regional' if level in ('regional', 'region') else 'municipal'

        new_entity = {
            'entity_name': data.get('name', ''),
            'entity_level': normalized_level,
            'region_name': data.get('parent_region', ''),
            'municipality_name': data.get('municipality', '') if normalized_level == 'municipal' else '',
            'bank_account_number': data.get('bank_account', ''),
            'status': 'active',
            'created_at': datetime.now(),
            'updated_at': datetime.now()
        }

        db.collection('entities').add(new_entity)
        return jsonify({'success': True, 'message': 'Entity created successfully'})
    except Exception as e:
        print(f'[ERROR] Failed to create entity: {e}')
        return jsonify({'success': False, 'error': str(e)}), 500


@bp.route('/accounting/entities')
@role_required('national', 'national_admin')
def accounting_entities():
    return render_template('national/accounting/accounting-entities.html')


@bp.route('/accounting/coa-templates')
@role_required('national', 'national_admin')
def accounting_coa_templates():
    return render_template('national/accounting/accounting-coa-templates.html')


@bp.route('/accounting/expense-categories')
@role_required('national', 'national_admin')
def accounting_expense_categories():
    return render_template('national/accounting/accounting-expense-categories.html')


@bp.route('/accounting/deposit-categories')
@role_required('national', 'national_admin')
def accounting_deposit_categories():
    return render_template('national/accounting/accounting-deposit-categories.html')

@bp.route('/transaction-national')
@role_required('national', 'national_admin')
def transaction_national_view():
    return render_template('national/accounting/transaction-national.html')


# -----------------------------
# PROFILE (National)
# -----------------------------
@bp.route('/profile-national')
@role_required('national', 'national_admin')
def profile_national_view():
    return render_template('national/system/profile-national.html')

@bp.route('/company')
@role_required('national', 'national_admin')
def company_national_view():
    return render_template('national/HRM/company-national.html')

@bp.route('/departments')
@role_required('national', 'national_admin')
def departments_national_view():
    return render_template('national/HRM/department-national.html')

@bp.route('/designations')
@role_required('national', 'national_admin')
def designations_national_view():
    return render_template('national/HRM/designation-national.html')

@bp.route('/office-shifts')
@role_required('national', 'national_admin')
def office_shifts_national_view():
    return render_template('national/HRM/office-shift-national.html')

@bp.route('/employees')
@role_required('national', 'national_admin')
def employees_national_view():
    return render_template('national/HRM/employees-national.html')

@bp.route('/attendance')
@role_required('national', 'national_admin')
def attendance_national_view():
    return render_template('national/HRM/attendance-national.html')

@bp.route('/holidays')
@role_required('national', 'national_admin')
def holidays_national_view():
    return render_template('national/HRM/holiday-national.html')

@bp.route('/leave-requests')
@role_required('national', 'national_admin')
def leave_requests_national_view():
    # Debug: Print session info for diagnosis
    print("[DEBUG] /national/leave-requests accessed")
    print("[DEBUG] session:", dict(session))
    print("[DEBUG] user_role:", session.get('user_role'))
    print("[DEBUG] user_email:", session.get('user_email'))
    return render_template('national/HRM/leave-request-national.html')

@bp.route('/payroll')
@role_required('national', 'national_admin')
def payroll_national_view():
    return render_template('national/operations/payroll-national.html')

@bp.route('/audit-logs')
@role_required('national', 'national_admin')
def audit_logs():
    # Always refresh the audit logs from regional/transactions before displaying
    try:
        aggregate_regional_audit_logs_to_national()
    except Exception as e:
        print(f"[ERROR] Audit log aggregation failed: {e}")
    db = get_firestore_db()
    logs = []
    try:
        docs = db.collection('national_audit_logs').order_by('timestamp', direction=firestore.Query.DESCENDING).limit(200).stream()
        for doc in docs:
            entry = doc.to_dict() or {}
            # Prefer email if available, fallback to name, then 'User'
            user_val = entry.get('user') or entry.get('user_email') or entry.get('actorEmail') or entry.get('actorName') or entry.get('actor') or 'User'
            logs.append({
                'timestamp': entry.get('timestamp') or '',
                'user': user_val,
                'entity': entry.get('entity') or '',
                'action': entry.get('action') or '',
                'details': entry.get('details') or '',
                'ip': entry.get('ip') or '',
            })
    except Exception as e:
        print(f"[ERROR] Failed to fetch national audit logs: {e}")
    return render_template('national/system/audit.html', audit_logs=logs)


# --- SYSTEM LOGS (National) ---
@bp.route('/system-logs')
@role_required('national', 'national_admin')
def system_logs():
    try:
        # Fetch last 40 logs from national_system_logs
        logs = list_national_system_logs(limit=40)
        # Normalize for template
        normalized_logs = []
        for entry in logs:
            normalized_logs.append({
                'timestamp': entry.get('timestamp') or entry.get('created_at') or entry.get('createdAt') or '',
                'user': entry.get('user') or entry.get('actorEmail') or entry.get('actor') or '',
                'action': entry.get('action') or entry.get('event') or entry.get('type') or '',
                'module': entry.get('module') or 'SYSTEM',
                'target': entry.get('target') or entry.get('targetId') or entry.get('module') or 'System',
                'targetId': entry.get('targetId') or entry.get('target_id') or entry.get('id') or '',
                'device_type': entry.get('device_type') or entry.get('device') or 'Unknown',
                'outcome': entry.get('outcome') or 'SUCCESS',
                'message': entry.get('message') or entry.get('details') or entry.get('description') or '',
                'municipality': entry.get('municipality') or entry.get('municipality_name') or '',
                'region': entry.get('region') or entry.get('region_name') or entry.get('regionName') or '',
                'role': entry.get('role') or '',
                'ip': entry.get('ip') or entry.get('ipAddress') or '',
            })
        return render_template(
            'national/system/system-logs.html',
            regional_logs=normalized_logs,
            municipal_logs=normalized_logs,
            user_logs=normalized_logs
        )
    except Exception as e:
        print(f"[ERROR] Failed to fetch national system logs: {e}")
        return render_template('national/system/system-logs.html',
            regional_logs=[],
            municipal_logs=[],
            user_logs=[]
        )

@bp.route('/permissions')
@role_required('national', 'national_admin')
def permissions_national_view():
    return render_template('national/system/permissions.html')

@bp.route('/service-requests')
@role_required('national', 'national_admin')
def service_requests_national_view():
    try:
        db = get_firestore_db()
        import calendar
        from collections import defaultdict

        def _to_datetime(value):
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
                    pass
            if hasattr(value, 'strftime'):
                return value
            return None

        # Pull forwarded-national (pending), AND approved/rejected that were handled at national level
        raw_docs = []
        raw_docs += list(db.collection('service_requests')
                           .where('status', '==', 'forwarded-national')
                           .stream())
        raw_docs += list(db.collection('service_requests')
                           .where('status', '==', 'approved')
                           .where('approvedByLevel', '==', 'National')
                           .stream())
        raw_docs += list(db.collection('service_requests')
                           .where('status', '==', 'rejected')
                           .where('rejectedByLevel', '==', 'National')
                           .stream())

        # Deduplicate by doc id
        seen = set()
        docs = []
        for d in raw_docs:
            if d.id not in seen:
                seen.add(d.id)
                docs.append(d)

        # Batch-fetch all unique user docs
        user_ids = list({d.to_dict().get('userId') for d in docs if d.to_dict().get('userId')})
        users_map = {}
        for uid in user_ids:
            try:
                u = db.collection('users').document(uid).get()
                if u.exists:
                    users_map[uid] = u.to_dict()
            except Exception:
                pass

        service_requests = []
        monthly_trend = defaultdict(int)
        service_type_count = defaultdict(int)
        status_breakdown = defaultdict(int)

        for doc in docs:
            data = doc.to_dict()

            # Date
            created_at = data.get('createdAt') or data.get('submittedAt')
            created_dt = _to_datetime(created_at)
            date_filed = 'N/A'
            if created_dt:
                try:
                    date_filed = created_dt.strftime('%b %d, %Y')
                except Exception:
                    date_filed = str(created_at)
            elif created_at:
                date_filed = str(created_at)

            # Applicant name — from users collection via userId
            uid = data.get('userId', '')
            user_data = users_map.get(uid, {})
            first = user_data.get('firstName', '')
            last  = user_data.get('lastName', '')
            full_name = f"{first} {last}".strip() or user_data.get('email', data.get('userEmail', 'N/A'))

            # Location — from service doc fields, fallback to user profile
            province     = data.get('province')     or user_data.get('province', '')
            municipality = data.get('municipality') or user_data.get('municipality', '')
            barangay     = data.get('barangay')     or user_data.get('barangay', '')
            location_parts = [p for p in [barangay, municipality, province] if p]
            location = ', '.join(location_parts) if location_parts else 'N/A'

            doc_status = (data.get('status') or 'forwarded-national').lower()
            approved_by_level = data.get('approvedByLevel', '')

            if created_dt:
                month_key = created_dt.strftime('%Y-%m')
                monthly_trend[month_key] += 1

            service_type = data.get('serviceType', 'N/A') or 'N/A'
            service_type_count[service_type] += 1

            if doc_status == 'approved':
                status_breakdown['approved'] += 1
            elif doc_status == 'rejected':
                status_breakdown['rejected'] += 1
            else:
                status_breakdown['pending'] += 1

            service_requests.append({
                'id': doc.id,
                'date_filed': date_filed,
                'sort_dt': created_dt,
                'reference_id': doc.id[:10].upper(),
                'applicant_name': full_name.upper(),
                'service_type': service_type,
                'location': location,
                'status': doc_status,
                'approved_by_level': approved_by_level,
                'forwarded_by': data.get('forwardedToNationalBy', 'N/A'),
            })

        service_requests.sort(
            key=lambda x: x.get('sort_dt') or datetime.min,
            reverse=True
        )

        current_date = datetime.now()
        trend_labels = []
        trend_data = []
        for i in range(5, -1, -1):
            month = current_date.month - i
            year = current_date.year
            while month <= 0:
                month += 12
                year -= 1
            month_key = f'{year}-{month:02d}'
            trend_labels.append(calendar.month_abbr[month])
            trend_data.append(monthly_trend.get(month_key, 0))

        top_service_types = sorted(service_type_count.items(), key=lambda x: x[1], reverse=True)[:6]
        service_labels = [item[0] for item in top_service_types] if top_service_types else ['N/A']
        service_counts = [item[1] for item in top_service_types] if top_service_types else [0]

        status_labels = ['Approved', 'Pending', 'Rejected']
        status_data = [
            status_breakdown.get('approved', 0),
            status_breakdown.get('pending', 0),
            status_breakdown.get('rejected', 0)
        ]

        total_count    = len(service_requests)
        completed_count = sum(1 for r in service_requests if r['status'] == 'approved')
        rejected_count  = sum(1 for r in service_requests if r['status'] == 'rejected')
        pending_count   = sum(1 for r in service_requests if r['status'] not in ('approved', 'rejected'))

    except Exception as e:
        print(f'Error loading national service requests: {e}')
        service_requests = []
        total_count = completed_count = rejected_count = pending_count = 0
        trend_labels = ['S', 'O', 'N', 'D', 'J', 'F']
        trend_data = [0, 0, 0, 0, 0, 0]
        service_labels = ['N/A']
        service_counts = [0]
        status_labels = ['Approved', 'Pending', 'Rejected']
        status_data = [0, 0, 0]

    return render_template('national/operations/service-national.html',
                           service_requests=service_requests,
                           total_count=total_count,
                           completed_count=completed_count,
                           pending_count=pending_count,
                           rejected_count=rejected_count,
                           trend_labels=trend_labels,
                           trend_data=trend_data,
                           service_labels=service_labels,
                           service_counts=service_counts,
                           status_labels=status_labels,
                           status_data=status_data)

@bp.route('/user-inventory')
@role_required('national', 'national_admin')
def user_inventory_national():
    return render_template('national/logistics/user-inventory-national.html')

@bp.route('/system-logs')
@role_required('national', 'national_admin')
def system_logs_national():
    return render_template('national/system/system-logs.html')

@bp.route('/accounting/deposits')
@role_required('national', 'national_admin')
def national_deposits_view():
    """National level payment deposits dashboard (all regions/municipalities)"""
    return render_template('national/accounting/payment-deposits-national.html')

# ---------------------------------
# EXPENSE CATEGORIES (National)
# ---------------------------------
@bp.route('/api/expense-categories', methods=['GET'])
@role_required('national', 'national_admin')
def api_get_national_expense_categories():
    """Get ALL expense categories from all municipalities (National view)"""
    try:
        from expense_storage import get_all_expense_categories
        categories = get_all_expense_categories()
        print(f'[INFO] National: Retrieved {len(categories)} expense categories')
        return jsonify(categories), 200
        
    except Exception as e:
        print(f'[ERROR] National: Failed to get expense categories: {e}')
        return jsonify({'error': str(e)}), 500

@bp.route('/api/expense-categories', methods=['POST'])
@role_required('national', 'national_admin')
def api_create_national_expense_category():
    """Create a new expense category (National admin only)"""
    try:
        from flask import request
        data = request.get_json()
        
        db = get_firestore_db()
        new_category = {
            'name': data.get('name', 'Unnamed'),
            'coa_code': data.get('coa_code', ''),
            'tax_type': data.get('tax_type', 'None'),
            'default_rate': data.get('default_rate', 0),
            'status': data.get('status', 'active'),
            'municipality': 'National',
            'created_at': datetime.utcnow()
        }
        
        doc_ref = db.collection('expense_categories').document()
        doc_ref.set(new_category)
        
        print(f'[INFO] National: Created expense category {doc_ref.id}')
        return jsonify({'id': doc_ref.id, **new_category}), 201
        
    except Exception as e:
        print(f'[ERROR] National: Failed to create category: {e}')
        return jsonify({'error': str(e)}), 500

@bp.route('/api/expense-categories/<category_id>', methods=['PUT'])
@role_required('national', 'national_admin')
def api_update_national_expense_category(category_id):
    """Update an expense category"""
    try:
        from flask import request
        data = request.get_json()
        
        db = get_firestore_db()
        doc_ref = db.collection('expense_categories').document(category_id)
        
        update_data = {
            'name': data.get('name'),
            'coa_code': data.get('coa_code'),
            'tax_type': data.get('tax_type'),
            'default_rate': data.get('default_rate'),
            'status': data.get('status'),
            'updated_at': datetime.utcnow()
        }
        
        doc_ref.update(update_data)
        
        print(f'[INFO] National: Updated expense category {category_id}')
        return jsonify({'id': category_id, **update_data}), 200
        
    except Exception as e:
        print(f'[ERROR] National: Failed to update category: {e}')
        return jsonify({'error': str(e)}), 500

@bp.route('/api/expense-categories/<category_id>', methods=['DELETE'])
@role_required('national', 'national_admin')
def api_delete_national_expense_category(category_id):
    """Delete an expense category"""
    try:
        db = get_firestore_db()
        db.collection('expense_categories').document(category_id).delete()
        
        print(f'[INFO] National: Deleted expense category {category_id}')
        return jsonify({'success': True}), 200
        
    except Exception as e:
        print(f'[ERROR] National: Failed to delete category: {e}')
        return jsonify({'error': str(e)}), 500

# ---------------------------------
# PAYMENT DEPOSITS (National)
# ---------------------------------
@bp.route('/api/deposits/payments', methods=['GET'])
@role_required('national', 'national_admin')
def api_get_national_payment_deposits():
    """Get ALL payment transactions from all regions/municipalities (National view)"""
    try:
        print('[DEBUG] National: Fetching ALL payment deposits')
        
        db = get_firestore_db()
        deposits = []
        
        paid_markers = {'paid', 'completed', 'settled', 'approved', 'success', 'succeeded'}
        
        def parse_amount(raw_value):
            try:
                return float(raw_value or 0)
            except (ValueError, TypeError):
                return 0.0
        
        def is_paid(status_value):
            return str(status_value or '').strip().lower() in paid_markers
        
        # Fetch ALL transactions without any filtering
        try:
            all_transactions = db.collection('transactions').limit(5000).stream()
            
            for doc in all_transactions:
                trans = doc.to_dict()
                if not trans:
                    continue
                
                status = trans.get('status') or trans.get('paymentStatus') or trans.get('payment_status')
                paid_by_status = is_paid(status)
                paid_by_method = bool(trans.get('payment_method')) and str(status or '').strip().lower() not in {'pending', 'failed', 'expired', 'cancelled'}
                amount = parse_amount(trans.get('amount'))
                
                # Only include paid/completed transactions
                if amount > 0 and (paid_by_status or paid_by_method):
                    deposits.append({
                        'id': doc.id,
                        'transaction_type': 'Payment Deposit',
                        'payment_type': 'Online Payment',
                        'invoice_id': trans.get('invoice_id', ''),
                        'external_id': trans.get('external_id', ''),
                        'amount': amount,
                        'description': trans.get('description', trans.get('transaction_name', 'Payment')),
                        'payer_email': trans.get('user_email', '').lower(),
                        'payment_method': trans.get('payment_method', 'Unknown'),
                        'status': str(status or '').strip().upper(),
                        'created_at': trans.get('created_at', trans.get('createdAt', '')),
                        'paid_at': trans.get('paid_at', trans.get('paidAt', '')),
                        'reference': trans.get('reference_id', doc.id[:12]),
                        'source': trans.get('source', 'Online Portal'),
                        'municipality': trans.get('municipality', trans.get('municipality_name', 'N/A')),
                        'region': trans.get('region', trans.get('region_name', trans.get('regionName', 'N/A'))),
                    })
        except Exception as e:
            print(f'[ERROR] National: Failed to fetch transactions: {e}')
            return jsonify({'error': str(e)}), 500
        
        print(f'[INFO] National: Retrieved {len(deposits)} payment deposits from ALL regions/municipalities')
        return jsonify(deposits), 200
        
    except Exception as e:
        print(f'[ERROR] National: Failed to get payment deposits: {e}')
        return jsonify({'error': str(e)}), 500


@bp.route('/api/transactions/all', methods=['GET'])
@role_required('national', 'national_admin')
def api_get_all_national_transactions():
    """Get ALL transactions from all regions/municipalities with region, type, and user details (National Transaction Registry)"""
    try:
        print('[DEBUG] National: Fetching ALL transactions (paid & refunded)')

        db = get_firestore_db()
        transactions = []

        def parse_amount(raw_value):
            try:
                return float(raw_value or 0)
            except (ValueError, TypeError):
                return 0.0

        def first_non_empty(values):
            for value in values:
                text = str(value or '').strip()
                if text:
                    return text
            return ''

        def get_transaction_type(description, trans_type=None):
            """Infer transaction type from description or field"""
            if trans_type:
                return str(trans_type).title()
            desc = str(description or '').lower()
            if 'permit' in desc or 'license' in desc:
                return 'Licensing/Permit'
            if 'service' in desc:
                return 'Service Request'
            if 'application' in desc:
                return 'Application'
            return 'General Payment'

        def get_transaction_status(status_field):
            """Determine if transaction is Paid or Refunded"""
            status_str = str(status_field or '').strip().lower()
            paid_markers = {'paid', 'completed', 'settled', 'approved', 'success', 'succeeded'}
            refunded_markers = {'refunded', 'cancelled', 'rejected'}

            if status_str in refunded_markers:
                return 'Refunded'
            elif status_str in paid_markers:
                return 'Paid'
            else:
                return 'Pending'

        user_cache = {}

        def get_user_profile(email, user_id):
            cache_key = (str(email or '').lower(), str(user_id or ''))
            if cache_key in user_cache:
                return user_cache[cache_key]

            profile = None
            email_value = str(email or '').strip().lower()
            user_id_value = str(user_id or '').strip()

            try:
                if email_value:
                    doc = db.collection('users').document(email_value).get()
                    if doc.exists:
                        profile = doc.to_dict() or {}

                if not profile and user_id_value:
                    doc = db.collection('users').document(user_id_value).get()
                    if doc.exists:
                        profile = doc.to_dict() or {}

                if not profile and email_value:
                    docs = db.collection('users').where(filter=FieldFilter('email', '==', email_value)).limit(1).stream()
                    for item in docs:
                        profile = item.to_dict() or {}
                        break
            except Exception as user_lookup_error:
                print(f"[DEBUG] User lookup failed for {email_value or user_id_value}: {user_lookup_error}")

            user_cache[cache_key] = profile or {}
            return user_cache[cache_key]

        def get_user_info(trans_data):
            """Extract comprehensive user information from transaction"""
            user_email = first_non_empty([
                trans_data.get('user_email'),
                trans_data.get('email'),
                trans_data.get('payer_email'),
                trans_data.get('customer_email')
            ]).lower()
            user_name = first_non_empty([
                trans_data.get('user_name'),
                trans_data.get('userName'),
                trans_data.get('fullName'),
                trans_data.get('name'),
                trans_data.get('customer_name')
            ])
            user_id = first_non_empty([
                trans_data.get('user_id'),
                trans_data.get('userId'),
                trans_data.get('uid')
            ])

            if not user_name and user_email:
                user_name = user_email.split('@')[0]

            user_profile = get_user_profile(user_email, user_id)
            if user_profile:
                profile_name = first_non_empty([
                    user_profile.get('display_name'),
                    user_profile.get('fullName'),
                    user_profile.get('name'),
                    f"{str(user_profile.get('firstName', '')).strip()} {str(user_profile.get('lastName', '')).strip()}".strip(),
                ])
                if profile_name:
                    user_name = profile_name

            return user_email, user_name or 'Unknown User', user_profile

        def get_location_info(trans_data, user_profile):
            """Resolve location from transaction, metadata, user profile, then related docs."""
            metadata = trans_data.get('metadata') if isinstance(trans_data.get('metadata'), dict) else {}

            region = first_non_empty([
                trans_data.get('region'),
                trans_data.get('region_name'),
                trans_data.get('regionName'),
                trans_data.get('user_region'),
                metadata.get('region'),
                metadata.get('region_name'),
                metadata.get('regionName'),
            ])
            municipality = first_non_empty([
                trans_data.get('municipality'),
                trans_data.get('municipality_name'),
                trans_data.get('municipalityName'),
                trans_data.get('user_municipality'),
                metadata.get('municipality'),
                metadata.get('municipality_name'),
                metadata.get('municipalityName'),
            ])

            if user_profile and (not region or not municipality):
                region = region or first_non_empty([
                    user_profile.get('region'),
                    user_profile.get('region_name'),
                    user_profile.get('regionName'),
                    user_profile.get('user_region'),
                ])
                municipality = municipality or first_non_empty([
                    user_profile.get('municipality'),
                    user_profile.get('municipality_name'),
                    user_profile.get('municipalityName'),
                    user_profile.get('user_municipality'),
                ])

            related_id = first_non_empty([
                trans_data.get('related_id'),
                trans_data.get('applicationId'),
                trans_data.get('application_id'),
                trans_data.get('service_request_id'),
                metadata.get('application_id'),
                metadata.get('service_request_id'),
            ])
            if related_id and (not region or not municipality):
                for collection_name in ['applications', 'service_requests', 'licenses', 'permits']:
                    try:
                        rel_doc = db.collection(collection_name).document(related_id).get()
                        if not rel_doc.exists:
                            continue
                        rel_data = rel_doc.to_dict() or {}
                        region = region or first_non_empty([
                            rel_data.get('region'),
                            rel_data.get('region_name'),
                            rel_data.get('regionName'),
                        ])
                        municipality = municipality or first_non_empty([
                            rel_data.get('municipality'),
                            rel_data.get('municipality_name'),
                            rel_data.get('municipalityName'),
                        ])
                        if region and municipality:
                            break
                    except Exception:
                        continue

            return region or 'N/A', municipality or 'N/A'

        try:
            # Fetch ALL transactions (no filtering)
            all_trans = db.collection('transactions').limit(5000).stream()

            for doc in all_trans:
                trans = doc.to_dict()
                if not trans:
                    continue

                amount = parse_amount(trans.get('amount'))
                if amount <= 0:
                    continue

                status = trans.get('status') or trans.get('paymentStatus') or trans.get('payment_status') or 'pending'
                trans_status = get_transaction_status(status)

                user_email, user_name, user_profile = get_user_info(trans)
                region, municipality = get_location_info(trans, user_profile)

                created_at = trans.get('created_at') or trans.get('createdAt') or ''
                if isinstance(created_at, object) and hasattr(created_at, 'timestamp'):
                    created_at = created_at.timestamp() * 1000

                transactions.append({
                    'id': doc.id,
                    'reference': trans.get('invoice_id', trans.get('reference_id', doc.id[:12])),
                    'name': user_name,
                    'email': user_email,
                    'type': get_transaction_type(trans.get('description'), trans.get('transaction_type')),
                    'created_at': created_at,
                    'date': trans.get('date', created_at),
                    'location': f"{region}, {municipality}",
                    'region': region,
                    'municipality': municipality,
                    'status': trans_status,
                    'amount': amount,
                    'description': trans.get('description', ''),
                    'payment_method': trans.get('payment_method', 'Unknown'),
                })

        except Exception as e:
            print(f'[ERROR] National: Failed to fetch transactions: {e}')
            return jsonify({'error': str(e)}), 500

        # Sort by date descending
        transactions.sort(key=lambda x: x['created_at'], reverse=True)

        print(f'[INFO] National: Retrieved {len(transactions)} transactions from ALL regions/municipalities')
        return jsonify(transactions), 200

    except Exception as e:
        print(f'[ERROR] National: Failed to get transactions: {e}')
        return jsonify({'error': str(e)}), 500


@bp.route('/operations/quotation/api/<quotation_id>/status', methods=['POST'])
@role_required('national', 'national_admin')
def quotations_national_update_status(quotation_id):
    from quotation_storage import update_quotation
    data = request.get_json(silent=True) or {}
    status = str(data.get('status') or '').strip().upper()
    if status not in {'PENDING', 'APPROVED', 'REJECTED'}:
        return jsonify({'success': False, 'error': 'Invalid status'}), 400
    try:
        updated = update_quotation(quotation_id, {'status': status})
        if not updated:
            return jsonify({'success': False, 'error': 'Quotation not found'}), 404
        return jsonify({'success': True})
    except Exception as e:
        print(f"[ERROR] quotations_national_update_status failed: {e}")
        return jsonify({'success': False, 'error': 'Failed to update quotation status'}), 500

@bp.route('/operations/quotation/api/<quotation_id>', methods=['DELETE'])
@role_required('national', 'national_admin')
def quotations_national_delete(quotation_id):
    from quotation_storage import delete_quotation
    try:
        delete_quotation(quotation_id)
        return jsonify({'success': True})
    except Exception as e:
        print(f"[ERROR] quotations_national_delete failed: {e}")
        return jsonify({'success': False, 'error': 'Failed to delete quotation'}), 500
    
    

# Endpoint: Update permissions for a specific admin
@bp.route('/api/admins-permissions/<user_id>', methods=['POST'])
@role_required('national', 'national_admin')
def api_update_admin_permissions(user_id):
    db = get_firestore_db()
    data = request.get_json(force=True)
    permissions = data.get('permissions', {})
    user_ref = db.collection('users').document(user_id)
    user_ref.update({'permissions': permissions})
    return jsonify({'success': True, 'message': 'Permissions updated.'})

@bp.route('/api/admins-permissions', methods=['GET'])
@role_required('national', 'national_admin')
def api_get_admins_permissions():
    db = get_firestore_db()
    users_ref = db.collection('users')
    users = []
    count = 0
    for user_doc in users_ref.stream():
        user = user_doc.to_dict() or {}
        role = user.get('role', '').lower()
        if role in ['regional_admin', 'regional', 'municipal_admin', 'municipal']:
            perms = user.get('permissions', {}) or {}
            # Default: all access if missing or incomplete
            perms = {
                'hrm': perms.get('hrm', True),
                'logistics': perms.get('logistics', True),
                'accounting': perms.get('accounting', True),
                'payments': perms.get('payments', True),
                'other': perms.get('other', True)
            }
            users.append({
                'id': user_doc.id,
                'email': user.get('email', ''),
                'name': f"{user.get('firstName', '')} {user.get('lastName', '')}".strip(),
                'role': role,
                'region': user.get('region', ''),
                'municipality': user.get('municipality', ''),
                'permissions': perms
            })
            count += 1
    print(f"[DEBUG] /api/admins-permissions: Found {count} admin users: {[u['role'] for u in users]}")
    return jsonify({'admins': users})


@bp.route('/api/user-management/accounts', methods=['GET'])
@role_required('national', 'national_admin')
def api_get_all_admin_accounts():
    """Fetch all regional and municipal admin accounts for national user management."""
    try:
        db = get_firestore_db()
        users_ref = db.collection('users')
        users = []
        for doc in users_ref.stream():
            data = doc.to_dict() or {}
            role = data.get('role', '').lower()
            # Match any role containing 'regional' or 'municipal'
            if 'regional' in role or 'municipal' in role:
                data['id'] = doc.id
                data['name'] = f"{data.get('firstName', '')} {data.get('lastName', '')}".strip()
                data['status'] = data.get('status', 'Active')
                users.append(data)
        return jsonify({'success': True, 'users': users})
    except Exception as e:
        print(f"[ERROR] Failed to fetch admin accounts: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@bp.route('/api/user-management/accounts/<user_id>/revoke', methods=['POST'])
@role_required('national', 'national_admin')
def api_revoke_admin_account(user_id):
    """Revoke (disable) a regional or municipal admin account."""
    try:
        db = get_firestore_db()
        user_ref = db.collection('users').document(user_id)
        user_doc = user_ref.get()
        if not user_doc.exists:
            return jsonify({'success': False, 'error': 'User not found'}), 404
        user_ref.update({'status': 'Disabled'})
        return jsonify({'success': True})
    except Exception as e:
        print(f"[ERROR] Failed to revoke admin account: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
    

@bp.route('/api/holidays/<holiday_id>/approve', methods=['POST'])
@role_required('national', 'national_admin')
def approve_national_holiday(holiday_id):
    db = get_firestore_db()
    ref = db.collection('holidays').document(holiday_id)
    ref.update({'status': 'approved'})
    return jsonify({'success': True})

@bp.route('/api/holidays/<holiday_id>/reject', methods=['POST'])
@role_required('national', 'national_admin')
def reject_national_holiday(holiday_id):
    db = get_firestore_db()
    ref = db.collection('holidays').document(holiday_id)
    ref.update({'status': 'rejected'})
    return jsonify({'success': True})
@bp.route('/api/holidays', methods=['GET'])
@role_required('national', 'national_admin')
def get_national_holidays():
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
            'status': item.get('status', 'approved')
        })

    return jsonify({'success': True, 'holidays': holidays})


@bp.route('/api/employees', methods=['GET'])
@role_required('national', 'national_admin')
def api_get_national_employees():
    """Fetch all employees from all regions/municipalities for national payroll registry"""
    try:
        db = get_firestore_db()
        employees_ref = db.collection('employees')
        docs = employees_ref.stream()
        employees = []
        for doc in docs:
            data = doc.to_dict()
            data['id'] = doc.id
            employees.append(data)
        return jsonify({'success': True, 'employees': employees, 'count': len(employees)})
    except Exception as e:
        print(f'[ERROR] Failed to fetch employees: {e}')
        return jsonify({'success': False, 'error': str(e)}), 500
    

from google.cloud.firestore_v1.base_query import FieldFilter
def aggregate_regional_audit_logs_to_national():
    """Aggregate audit logs and transactions from all regions into national_audit_logs collection."""
    db = get_firestore_db()
    regions = [
        'NCR', 'REGION-I', 'REGION-II', 'REGION-III', 'REGION-IV-A', 'REGION-IV-B', 'REGION-V',
        'REGION-VI', 'REGION-VII', 'REGION-VIII', 'REGION-IX', 'REGION-X', 'REGION-XI',
        'REGION-XII', 'REGION-XIII', 'CAR', 'REGION-BANGSAMORO'
    ]
    batch = db.batch()
    count = 0
    for region in regions:
        # Fetch auditLogs for each region
        audit_docs = db.collection('auditLogs').where(filter=FieldFilter('region', '==', region)).limit(1000).stream()
        for doc in audit_docs:
            entry = doc.to_dict() or {}
            log = {
                'timestamp': entry.get('timestamp') or entry.get('created_at') or entry.get('createdAt') or '',
                'user': entry.get('actorName') or entry.get('actor') or entry.get('user') or entry.get('actorEmail') or '',
                'entity': region,
                'action': entry.get('action') or entry.get('event') or entry.get('type') or '',
                'details': entry.get('detail') or entry.get('description') or entry.get('message') or '',
                'ip': entry.get('ip') or entry.get('ipAddress') or '',
            }
            ref = db.collection('national_audit_logs').document(f"{region}_{doc.id}")
            batch.set(ref, log)
            count += 1
        # Fetch transactions for each region
        tx_docs = db.collection('transactions').where(filter=FieldFilter('region', '==', region)).limit(1000).stream()
        for doc in tx_docs:
            tx = doc.to_dict() or {}
            log = {
                'timestamp': tx.get('updated_at') or tx.get('created_at') or tx.get('createdAt') or '',
                'user': tx.get('updated_by') or tx.get('forwarded_by') or tx.get('user_email') or 'User',
                'entity': region,
                'action': tx.get('status') or '',
                'details': tx.get('description') or '',
                'ip': tx.get('ip') or tx.get('ipAddress') or '',
            }
            ref = db.collection('national_audit_logs').document(f"{region}_tx_{doc.id}")
            batch.set(ref, log)
            count += 1

    # --- NATIONAL SCOPE: Aggregate all payment-related logs ---
    # 1. All transactions (national scope)
    tx_docs = db.collection('transactions').limit(5000).stream()
    for doc in tx_docs:
        tx = doc.to_dict() or {}
        log = {
            'timestamp': tx.get('updated_at') or tx.get('created_at') or tx.get('createdAt') or '',
            'user': tx.get('updated_by') or tx.get('forwarded_by') or tx.get('user_email') or 'User',
            'entity': tx.get('region') or 'NATIONAL',
            'action': tx.get('status') or '',
            'details': tx.get('description') or '',
            'ip': tx.get('ip') or tx.get('ipAddress') or '',
        }
        ref = db.collection('national_audit_logs').document(f"NATIONAL_tx_{doc.id}")
        batch.set(ref, log)
        count += 1

    # 2. All regional fund distributions (national to regions)
    fund_docs = db.collection('regional_fund_distribution').limit(5000).stream()
    for doc in fund_docs:
        fund = doc.to_dict() or {}
        log = {
            'timestamp': fund.get('updated_at') or fund.get('created_at') or fund.get('date') or '',
            'user': fund.get('updated_by') or fund.get('initiated_by') or 'National',
            'entity': fund.get('region') or 'NATIONAL',
            'action': fund.get('status') or '',
            'details': fund.get('description') or fund.get('fund_type') or '',
            'ip': fund.get('ip') or '',
        }
        ref = db.collection('national_audit_logs').document(f"NATIONAL_fund_{doc.id}")
        batch.set(ref, log)
        count += 1

    # 3. All municipal fund distributions (regions/national to municipalities)
    muni_fund_docs = db.collection('municipal_fund_distribution').limit(5000).stream()
    for doc in muni_fund_docs:
        fund = doc.to_dict() or {}
        log = {
            'timestamp': fund.get('updated_at') or fund.get('created_at') or fund.get('date') or '',
            'user': fund.get('updated_by') or fund.get('initiated_by') or 'National',
            'entity': fund.get('municipality') or 'NATIONAL',
            'action': fund.get('status') or '',
            'details': fund.get('description') or fund.get('fund_type') or '',
            'ip': fund.get('ip') or '',
        }
        ref = db.collection('national_audit_logs').document(f"NATIONAL_munifund_{doc.id}")
        batch.set(ref, log)
        count += 1

    # 4. All applications with payment info
    app_docs = db.collection('applications').limit(5000).stream()
    for doc in app_docs:
        app = doc.to_dict() or {}
        log = {
            'timestamp': app.get('updated_at') or app.get('created_at') or app.get('createdAt') or '',
            'user': app.get('updated_by') or app.get('user_email') or 'User',
            'entity': app.get('region') or 'NATIONAL',
            'action': app.get('status') or '',
            'details': app.get('description') or app.get('application_type') or '',
            'ip': app.get('ip') or app.get('ipAddress') or '',
        }
        ref = db.collection('national_audit_logs').document(f"NATIONAL_app_{doc.id}")
        batch.set(ref, log)
        count += 1

    # 5. All service requests with payment info
    sr_docs = db.collection('service_requests').limit(5000).stream()
    for doc in sr_docs:
        sr = doc.to_dict() or {}
        log = {
            'timestamp': sr.get('updated_at') or sr.get('created_at') or sr.get('createdAt') or '',
            'user': sr.get('updated_by') or sr.get('user_email') or 'User',
            'entity': sr.get('region') or 'NATIONAL',
            'action': sr.get('status') or '',
            'details': sr.get('description') or sr.get('service_type') or '',
            'ip': sr.get('ip') or sr.get('ipAddress') or '',
        }
        ref = db.collection('national_audit_logs').document(f"NATIONAL_sr_{doc.id}")
        batch.set(ref, log)
        count += 1

    # 6. All license applications (permits) with payment info
    permit_docs = db.collection('license_applications').limit(5000).stream()
    for doc in permit_docs:
        permit = doc.to_dict() or {}
        log = {
            'timestamp': permit.get('updated_at') or permit.get('created_at') or permit.get('createdAt') or '',
            'user': permit.get('updated_by') or permit.get('user_email') or 'User',
            'entity': permit.get('region') or 'NATIONAL',
            'action': permit.get('status') or '',
            'details': permit.get('description') or permit.get('applicationType') or '',
            'ip': permit.get('ip') or permit.get('ipAddress') or '',
        }
        ref = db.collection('national_audit_logs').document(f"NATIONAL_permit_{doc.id}")
        batch.set(ref, log)
        count += 1
    batch.commit()
    print(f"[INFO] Aggregated {count} audit logs to national_audit_logs.")

@bp.route('/aggregate-audit-logs')
@role_required('national', 'national_admin')
def aggregate_audit_logs_route():
    try:
        aggregate_regional_audit_logs_to_national()
        return jsonify({'success': True, 'message': 'Audit logs aggregated.'})
    except Exception as e:
        print(f"[ERROR] Failed to aggregate audit logs: {e}")
        return jsonify({'success': False, 'error': str(e)})



@bp.route('/api/projects/<project_id>/fully-complete', methods=['POST'])
@role_required('national', 'national_admin')
def mark_project_fully_completed_national(project_id):
    db = get_firestore_db()
    try:
        # Try to update in all possible project collections
        collections = [
            'municipal_projects',
            'regional_projects',
            'national_projects',
            'projects'
        ]
        found = False
        for col in collections:
            doc_ref = db.collection(col).document(project_id)
            doc = doc_ref.get()
            if doc.exists:
                doc_ref.update({
                    'municipal_completed': True,
                    'regional_completed': True,
                    'status': 'fully_completed'
                })
                found = True
                break
        if not found:
            return jsonify({'success': False, 'error': 'Project not found'}), 404
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
def record_national_audit_log(user, entity, action, details, ip=None, timestamp=None):
    """Helper to record a new audit log entry in national_audit_logs."""
    db = get_firestore_db()
    from datetime import datetime
    log = {
        'timestamp': timestamp or datetime.utcnow().isoformat(),
        'user': user,
        'entity': entity,
        'action': action,
        'details': details,
        'ip': ip or '',
    }
    db.collection('national_audit_logs').add(log)



@bp.route('/api/user-management/accounts/<user_id>/enable', methods=['POST'])
@role_required('national', 'national_admin')
def api_enable_admin_account(user_id):
    """Enable (restore) a regional or municipal admin account."""
    try:
        db = get_firestore_db()
        user_ref = db.collection('users').document(user_id)
        user_doc = user_ref.get()
        if not user_doc.exists:
            return jsonify({'success': False, 'error': 'User not found'}), 404
        user_ref.update({'status': 'Active'})
        return jsonify({'success': True})
    except Exception as e:
        print(f"[ERROR] Failed to enable admin account: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
    


@bp.route('/api/leave-requests', methods=['GET'])
@role_required('national', 'national_admin')
def api_get_national_leave_requests():
    """Fetch all leave requests with employee name and ID for national leave registry"""
    try:
        db = get_firestore_db()
        leave_docs = db.collection('leave_requests').stream()
        employee_docs = db.collection('employees').stream()

        # Build employee lookup by employee_id and doc id
        employees_by_id = {}
        employees_by_doc = {}
        for doc in employee_docs:
            emp = doc.to_dict() or {}
            emp_id = emp.get('employee_id') or doc.id
            name = emp.get('full_name') or emp.get('name') or f"{emp.get('firstName','')} {emp.get('lastName','')}".strip()
            employees_by_id[emp_id] = {'name': name, 'employee_id': emp_id}
            employees_by_doc[doc.id] = {'name': name, 'employee_id': emp_id}

        leave_requests = []
        for doc in leave_docs:
            data = doc.to_dict() or {}
            leave_id = doc.id
            emp_id = data.get('employee_id') or ''
            # Try to resolve employee name
            emp_info = employees_by_id.get(emp_id) or employees_by_doc.get(emp_id) or {}
            applicant_name = data.get('employee_name') or emp_info.get('name', 'N/A')
            employee_id = emp_id or emp_info.get('employee_id', leave_id)

            leave_requests.append({
                'id': leave_id,
                'employee_id': employee_id,
                'applicant_name': applicant_name,
                'leave_type': data.get('leave_type', ''),
                'from_date': data.get('from_date', ''),
                'to_date': data.get('to_date', ''),
                'days': data.get('days', 0),
                'purpose': data.get('reason', ''),
                'status': data.get('status', 'Pending'),
                'municipality': data.get('municipality', ''),
                'created_at': data.get('created_at', ''),
            })
        return jsonify({'success': True, 'leave_requests': leave_requests, 'count': len(leave_requests)})
    except Exception as e:
        print(f'[ERROR] Failed to fetch leave requests: {e}')
        return jsonify({'success': False, 'error': str(e)}), 500



@bp.route('/operations/quotation/api/create', methods=['POST'])
@role_required('national', 'national_admin')
def quotations_national_create():
    from quotation_storage import create_quotation
    data = request.get_json(silent=True) or {}
    try:
        # Map form fields to Firestore schema
        payload = {
            'number': data.get('number'),
            'client': data.get('client'),
            'amount_value': data.get('amount'),
            'date': data.get('date'),
            'status': data.get('status'),
            'region': data.get('region'),
            'municipality': data.get('municipality'),
            'description': data.get('description'),
            'scope': 'national',
            'created_by_role': 'national_admin',
        }
        result = create_quotation(payload)
        if not result:
            return jsonify({'success': False, 'error': 'Failed to create quotation'}), 500
        return jsonify({'success': True, 'id': result})
    except Exception as e:
        print(f"[ERROR] quotations_national_create failed: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
    


# --- Get Single Quotation (National) ---
@bp.route('/api/quotation/<quotation_id>', methods=['GET'])
@role_required('national', 'national_admin')
def get_quotation_national(quotation_id):
    from quotation_storage import get_quotation_by_id
    try:
        quotation = get_quotation_by_id(quotation_id)
        if not quotation:
            return jsonify({'success': False, 'error': 'Quotation not found'}), 404
        return jsonify(quotation)
    except Exception as e:
        print(f"[ERROR] get_quotation_national failed: {e}")
        return jsonify({'success': False, 'error': 'Failed to fetch quotation'}), 500

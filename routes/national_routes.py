from flask import Blueprint, render_template
from firebase_config import get_firestore_db
from datetime import datetime
from firebase_auth_middleware import role_required

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

                permits.append({
                    'id': doc.id,
                    'reference_id': doc.id[:12].upper(),
                    'applicant_name': full_name,
                    'classification': classification,
                    'location': location,
                    'region': region,
                    'date_filed': date_filed,
                    'status': national_status,
                    'regional_status': status,
                    'issue_date': issue_date,
                    'expiry_date': expiry_date
                })

        permits.sort(key=lambda x: x['date_filed'], reverse=True)

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

        inventory_ref = db.collection('license_applications')
        docs = inventory_ref.stream()

        inventory_records = []
        total_count = 0

        from collections import defaultdict
        category_count = defaultdict(int)
        region_count = defaultdict(int)

        for doc in docs:
            data = doc.to_dict()
            form_data = data.get('formData', {}) or {}

            full_name = form_data.get('fullName', 'N/A')
            municipality = form_data.get('municipality', 'N/A')
            region = form_data.get('region', 'N/A')

            app_type = data.get('applicationType', 'N/A')
            category_map = {
                'farm-visit': 'Chemical Inventory',
                'fishery-permit': 'Natural Resources',
                'livestock': 'Biodiversity Inventory',
                'forest': 'Natural Resources',
                'wildlife': 'Protected Area',
                'environment': 'Natural Resources'
            }
            category = category_map.get(str(app_type).lower(), 'Chemical Inventory')

            category_count[category] += 1

            if region and region != 'N/A':
                region_count[region] += 1

            total_count += 1

            quantity = data.get('quantity', 1)

            description_map = {
                'farm-visit': 'Registered Pesticide Stock',
                'fishery-permit': 'Marine Resources',
                'livestock': 'Animal Species Count',
                'forest': 'Forest Resources',
                'wildlife': 'Wildlife Species',
                'environment': 'Environmental Data'
            }
            description = description_map.get(str(app_type).lower(), 'General Inventory')

            inventory_records.append({
                'id': doc.id,
                'category': category,
                'description': description,
                'quantity': quantity,
                'region': region,
                'municipality': municipality,
                'applicant_name': full_name
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


@bp.route('/quotation')
@role_required('national', 'national_admin')
def quotation():
    return render_template('national/operations/quotation.html')


@bp.route('/projects')
@role_required('national', 'national_admin')
def projects():
    return render_template('national/operations/projects.html')


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
    return render_template('national/HRM/leave-request-national.html')

@bp.route('/payroll')
@role_required('national', 'national_admin')
def payroll_national_view():
    return render_template('national/HRM/payroll.html')

@bp.route('/audit-logs')
@role_required('national', 'national_admin')
def audit_logs():
    return render_template('national/system/audit.html')

@bp.route('/permissions')
@role_required('national', 'national_admin')
def permissions_national_view():
    return render_template('national/system/permissions.html')

@bp.route('/service-requests')
@role_required('national', 'national_admin')
def service_requests_national_view():
    return render_template('national/operations/service-national.html')

@bp.route('/user-inventory')
@role_required('national', 'national_admin')
def user_inventory_national():
    return render_template('national/logistics/user-inventory-national.html')
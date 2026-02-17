from flask import Blueprint, render_template, redirect, url_for, session
from firebase_auth_middleware import role_required, firebase_auth_required

bp = Blueprint('main', __name__)

@bp.route('/')
def index():
    print("HOME.HTML IS BEING RENDERED")  # Debug line
    return render_template('home.html')

@bp.route('/login')
def login():
    return render_template('login.html')

@bp.route('/register')
def register():
    return render_template('signup.html')

@bp.route('/create-municipal-admin')
def create_municipal_admin():
    return render_template('create-municipal-admin.html')

@bp.route('/create-regional-account')
def create_regional_account():
    return render_template('create_regional_account.html')

# Landing pages for different roles
@bp.route('/national/dashboard')
@role_required('national','national_admin')
def national_dashboard():
    try:
        from firebase_config import get_firestore_db
        from datetime import datetime
        from collections import defaultdict
        
        db = get_firestore_db()
        
        # Fetch all license applications (overview from all levels)
        applications_ref = db.collection('license_applications')
        app_docs = applications_ref.stream()
        
        applications = []
        total_applications = 0
        
        # For status breakdown
        status_counts = defaultdict(int)
        
        # For 6-month trend
        monthly_trend = defaultdict(int)
        
        for doc in app_docs:
            data = doc.to_dict()
            total_applications += 1
            
            # Count by status
            status = data.get('status', 'pending').lower()
            status_counts[status] += 1
            
            # Calculate monthly trend
            created_at = data.get('createdAt')
            if created_at:
                try:
                    if isinstance(created_at, str):
                        date_obj = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                    elif hasattr(created_at, 'strftime'):
                        date_obj = created_at
                    else:
                        date_obj = None
                    
                    if date_obj:
                        month_key = date_obj.strftime('%Y-%m')
                        monthly_trend[month_key] += 1
                except:
                    pass
            
            # Get form data
            form_data = data.get('formData', {})
            full_name = form_data.get('fullName', 'N/A')
            region = form_data.get('region', 'N/A')
            municipality = form_data.get('municipality', 'N/A')
            
            # Map application type
            app_type = data.get('applicationType', 'N/A')
            category_map = {
                'farm-visit': 'Crop & Plant',
                'fishery-permit': 'Fisheries',
                'livestock': 'Livestock',
                'forest': 'Forestry',
                'wildlife': 'Wildlife',
                'environment': 'Environmental'
            }
            category = category_map.get(app_type.lower(), app_type.upper())
            
            applications.append({
                'id': doc.id,
                'reference_id': doc.id[:12].upper(),
                'applicant_name': full_name,
                'category': category,
                'region': region,
                'municipality': municipality,
                'status': status,
                'created_at': created_at
            })
        
        # Fetch all service requests
        service_requests_ref = db.collection('service_requests')
        service_docs = service_requests_ref.stream()
        
        service_requests = []
        total_service_requests = 0
        
        for doc in service_docs:
            data = doc.to_dict()
            total_service_requests += 1
            
            # Count by status
            status = data.get('status', 'pending').lower()
            status_counts[status] += 1
            
            service_requests.append({
                'id': doc.id,
                'reference_id': doc.id[:10].upper(),
                'service_type': data.get('serviceType', 'N/A'),
                'region': data.get('region', 'N/A'),
                'municipality': data.get('municipality', 'N/A'),
                'status': status
            })
        
        # Calculate metrics
        approved_count = status_counts.get('approved', 0)
        pending_count = status_counts.get('pending', 0) + status_counts.get('to review', 0) + status_counts.get('review', 0)
        rejected_count = status_counts.get('rejected', 0)
        total_count = total_applications + total_service_requests
        
        # Calculate collections (placeholder - would need actual payment data)
        total_collections = total_applications * 1250.0  # Rough estimate
        
        # Prepare 6-month trend data
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
        
        # Sort applications by most recent
        applications.sort(key=lambda x: x.get('created_at', ''), reverse=True)
        
        return render_template('national/landing-national.html',
                             applications=applications[:10],  # Top 10 recent
                             service_requests=service_requests[:10],
                             total_applications=total_applications,
                             total_service_requests=total_service_requests,
                             total_count=total_count,
                             approved_count=approved_count,
                             pending_count=pending_count,
                             rejected_count=rejected_count,
                             total_collections=total_collections,
                             trend_labels=last_6_months,
                             trend_data=trend_data)
    except Exception as e:
        print(f"Error in national dashboard: {str(e)}")
        import traceback
        traceback.print_exc()
        # Return template with empty data on error
        return render_template('national/landing-national.html',
                             applications=[],
                             service_requests=[],
                             total_applications=0,
                             total_service_requests=0,
                             total_count=0,
                             approved_count=0,
                             pending_count=0,
                             rejected_count=0,
                             total_collections=0,
                             trend_labels=['Sep', 'Oct', 'Nov', 'Dec', 'Jan', 'Feb'],
                             trend_data=[0, 0, 0, 0, 0, 0])

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
def approval_status():
    return render_template('approval_status.html')

@bp.route('/payment-success')
def payment_success():
    return render_template('payment-success.html')

@bp.route('/payment-failed')
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

@bp.route('/user/inventory/info/<stock_id>')
@role_required('user')
def user_inventory_info(stock_id):
    return render_template('user/inventory/stock-info.html')

@bp.route('/user/inventory/history')
@role_required('user')
def user_inventory_history():
    return render_template('user/inventory/stock-history.html')

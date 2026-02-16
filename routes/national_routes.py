from flask import Blueprint, render_template
from firebase_config import get_firestore_db
from datetime import datetime

bp = Blueprint('national', __name__, url_prefix='/national')

@bp.route('/application-national')
def application_national_view():
    try:
        db = get_firestore_db()
        
        # Fetch only APPROVED applications from Regional (for National view)
        applications_ref = db.collection('license_applications').where('status', '==', 'approved')
        docs = applications_ref.stream()
        
        applications = []
        total_count = 0
        approved_count = 0
        pending_count = 0
        rejected_count = 0
        
        for doc in docs:
            data = doc.to_dict()
            
            # National only sees approved applications from Regional
            status = data.get('status', 'pending').lower()
            
            # Check if application has regional approval
            regional_status = data.get('regionalStatus', 'pending').lower()
            
            # Only include if approved by regional
            if status == 'approved':
                total_count += 1
                approved_count += 1
                
                # Format the application data
                created_at = data.get('createdAt')
                if created_at:
                    # Handle Firestore timestamp
                    if hasattr(created_at, 'strftime'):
                        date_filed = created_at.strftime('%b %d, %Y')
                    else:
                        date_filed = 'N/A'
                else:
                    date_filed = 'N/A'
                
                # Get form data
                form_data = data.get('formData', {})
                
                # Extract applicant name from form data
                full_name = form_data.get('fullName', 'N/A')
                
                # Extract location from form data
                region = form_data.get('region', 'N/A')
                municipality = form_data.get('municipality', 'N/A')
                location = f"{region} / {municipality}"
                
                # Map applicationType to category
                app_type = data.get('applicationType', 'N/A')
                category_map = {
                    'farm-visit': 'CROP & PLANT',
                    'fishery-permit': 'FISHERIES',
                    'livestock': 'LIVESTOCK & POULTRY',
                    'forest': 'FORESTRY',
                    'wildlife': 'WILDLIFE',
                    'environment': 'ENVIRONMENTAL'
                }
                category = category_map.get(app_type.lower(), app_type.upper())
                
                # Get approval details
                approved_by_regional = data.get('approvedByRegional', 'N/A')
                approval_date = data.get('approvalDate', 'N/A')
                
                applications.append({
                    'id': doc.id,
                    'date_filed': date_filed,
                    'reference_id': doc.id[:8].upper(),
                    'applicant_name': full_name,
                    'category': category,
                    'location': location,
                    'status': status,
                    'user_email': data.get('userEmail', 'N/A'),
                    'approved_by_regional': approved_by_regional,
                    'approval_date': approval_date
                })
        
        # Sort by most recent first
        applications.sort(key=lambda x: x['date_filed'], reverse=True)
        
        return render_template('national/applications-national.html',
                             applications=applications,
                             total_count=total_count,
                             approved_count=approved_count,
                             pending_count=pending_count,
                             rejected_count=rejected_count)
    except Exception as e:
        print(f"Error fetching applications: {str(e)}")
        # Return empty data on error
        return render_template('national/applications-national.html',
                             applications=[],
                             total_count=0,
                             approved_count=0,
                             pending_count=0,
                             rejected_count=0)

@bp.route('/permit-national')
def permit_national_view():
    return render_template('national/licensing-permit-national.html')

@bp.route('/service-national')
def service_national_view():
    try:
        db = get_firestore_db()
        
        # Fetch only APPROVED service requests from Regional (for National view)
        service_requests_ref = db.collection('service_requests').where('status', '==', 'approved')
        docs = service_requests_ref.stream()
        
        service_requests = []
        total_count = 0
        completed_count = 0
        pending_count = 0
        rejected_count = 0
        
        for doc in docs:
            data = doc.to_dict()
            
            # National only sees approved service requests from Regional
            status = data.get('status', 'pending').lower()
            
            # Only include if approved by regional
            if status == 'approved':
                total_count += 1
                completed_count += 1
                
                # Format the service request data
                created_at = data.get('createdAt')
                if created_at:
                    # Handle string dates or timestamps
                    if isinstance(created_at, str):
                        try:
                            date_obj = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                            date_filed = date_obj.strftime('%b %d, %Y')
                        except:
                            date_filed = created_at
                    elif hasattr(created_at, 'strftime'):
                        date_filed = created_at.strftime('%b %d, %Y')
                    else:
                        date_filed = 'N/A'
                else:
                    date_filed = 'N/A'
                
                # Extract service request details
                service_type = data.get('serviceType', 'N/A')
                user_email = data.get('userEmail', 'N/A')
                user_id = data.get('userId', 'N/A')
                
                # Get form data for additional details
                full_name = data.get('fullName', data.get('applicantName', 'N/A'))
                region = data.get('region', 'N/A')
                municipality = data.get('municipality', data.get('location', 'N/A'))
                location = f"{region} / {municipality}"
                
                # Get approval details
                approved_by_regional = data.get('approvedByRegional', 'N/A')
                approval_date = data.get('approvalDate', 'N/A')
                
                service_requests.append({
                    'id': doc.id,
                    'date_filed': date_filed,
                    'reference_id': doc.id[:10].upper(),
                    'applicant_name': full_name,
                    'service_type': service_type,
                    'location': location,
                    'status': status,
                    'user_email': user_email,
                    'approved_by_regional': approved_by_regional,
                    'approval_date': approval_date
                })
        
        # Sort by most recent first
        service_requests.sort(key=lambda x: x['date_filed'], reverse=True)
        
        return render_template('national/service-national.html',
                             service_requests=service_requests,
                             total_count=total_count,
                             completed_count=completed_count,
                             pending_count=pending_count,
                             rejected_count=rejected_count)
    except Exception as e:
        print(f"Error fetching service requests: {str(e)}")
        # Return empty data on error
        return render_template('national/service-national.html',
                             service_requests=[],
                             total_count=0,
                             completed_count=0,
                             pending_count=0,
                             rejected_count=0)

@bp.route('/inventory-national')
def inventory_national_view():
    return render_template('national/inventory-national.html')

@bp.route('/user-inventory-national')
def user_inventory_national_view():
    return render_template('national/user-inventory-national.html')

@bp.route('/transaction-national')
def transaction_national_view():
    return render_template('national/transaction-national.html')

@bp.route('/user-management-national')
def user_management_national_view():
    return render_template('national/user-national.html')

@bp.route('/profile-national')
def profile_national_view():
    return render_template('national/profile-national.html')
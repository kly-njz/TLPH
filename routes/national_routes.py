from flask import Blueprint, render_template
from firebase_config import get_firestore_db
from datetime import datetime

bp = Blueprint('national', __name__, url_prefix='/national')

@bp.route('/application-national')
def application_national_view():
    try:
        db = get_firestore_db()
        
        # Fetch APPROVED and TO REVIEW applications from Regional (for National view)
        # When Regional clicks "to review", it goes to National for final approve/reject
        applications_ref = db.collection('license_applications')
        docs = applications_ref.stream()
        
        applications = []
        total_count = 0
        approved_count = 0
        pending_count = 0
        rejected_count = 0
        
        # For chart calculations
        from collections import defaultdict
        monthly_trend = defaultdict(int)
        region_count = defaultdict(int)
        status_breakdown = defaultdict(int)
        
        for doc in docs:
            data = doc.to_dict()
            
            # National sees approved AND to review applications from Regional
            status = data.get('status', 'pending').lower()
            
            # Only include if approved OR to review by regional
            if status in ['approved', 'to review', 'review']:
                total_count += 1
                
                # For National, check nationalStatus for counting
                national_status = data.get('nationalStatus', 'pending').lower()
                if national_status == 'approved':
                    approved_count += 1
                elif national_status == 'rejected':
                    rejected_count += 1
                else:
                    pending_count += 1
                
                # Format the application data
                created_at = data.get('createdAt')
                date_obj = None
                if created_at:
                    # Handle Firestore timestamp
                    if isinstance(created_at, str):
                        try:
                            date_obj = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                            date_filed = date_obj.strftime('%b %d, %Y')
                        except:
                            date_filed = created_at
                    elif hasattr(created_at, 'strftime'):
                        date_obj = created_at
                        date_filed = created_at.strftime('%b %d, %Y')
                    else:
                        date_filed = 'N/A'
                else:
                    date_filed = 'N/A'
                
                # Calculate monthly trend for last 6 months
                if date_obj:
                    month_key = date_obj.strftime('%Y-%m')
                    monthly_trend[month_key] += 1
                
                # Get form data
                form_data = data.get('formData', {})
                
                # Extract applicant name from form data
                full_name = form_data.get('fullName', 'N/A')
                
                # Extract location from form data
                region = form_data.get('region', 'N/A')
                municipality = form_data.get('municipality', 'N/A')
                location = f"{region} / {municipality}"
                
                # Count by region
                if region and region != 'N/A':
                    region_count[region] += 1
                
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
                
                # Count by status (for breakdown) - National only has approved/rejected/pending
                if national_status in ['approved', 'rejected']:
                    status_breakdown[national_status] += 1
                else:
                    status_breakdown['pending'] += 1
                
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
                    'status': national_status,  # Use nationalStatus for display
                    'regional_status': status,  # Keep regional status for reference
                    'user_email': data.get('userEmail', 'N/A'),
                    'approved_by_regional': approved_by_regional,
                    'approval_date': approval_date
                })
        
        # Sort by most recent first
        applications.sort(key=lambda x: x['date_filed'], reverse=True)
        
        # Prepare chart data - last 6 months
        import calendar
        current_date = datetime.now()
        last_6_months = []
        trend_data = []
        
        for i in range(5, -1, -1):
            # Calculate month and year
            target_month = current_date.month - i
            target_year = current_date.year
            
            # Handle negative months (previous year)
            while target_month <= 0:
                target_month += 12
                target_year -= 1
            
            month_key = f"{target_year}-{target_month:02d}"
            month_label = calendar.month_abbr[target_month]
            last_6_months.append(month_label)
            trend_data.append(monthly_trend.get(month_key, 0))
        
        # Top 5 regions by volume
        top_regions = sorted(region_count.items(), key=lambda x: x[1], reverse=True)[:5]
        region_labels = [item[0] for item in top_regions] if top_regions else ['N/A']
        region_counts = [item[1] for item in top_regions] if top_regions else [0]
        
        # Status breakdown - National only has Approved, Pending, Rejected (no "To Review")
        status_labels = ['Approved', 'Pending', 'Rejected']
        status_data = [
            status_breakdown.get('approved', 0),
            status_breakdown.get('pending', 0),
            status_breakdown.get('rejected', 0)
        ]
        
        return render_template('national/applications-national.html',
                             applications=applications,
                             total_count=total_count,
                             approved_count=approved_count,
                             pending_count=pending_count,
                             rejected_count=rejected_count,
                             # Chart data
                             trend_labels=last_6_months,
                             trend_data=trend_data,
                             region_labels=region_labels,
                             region_counts=region_counts,
                             status_labels=status_labels,
                             status_data=status_data)
    except Exception as e:
        print(f"Error fetching applications: {str(e)}")
        import traceback
        traceback.print_exc()
        # Return empty data on error
        return render_template('national/applications-national.html',
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
                             status_data=[0, 0, 0])

@bp.route('/permit-national')
def permit_national_view():
    try:
        db = get_firestore_db()
        
        # Fetch only APPROVED license/permit applications from Regional (for National view)
        permits_ref = db.collection('license_applications').where('status', '==', 'approved')
        docs = permits_ref.stream()
        
        permits = []
        total_count = 0
        approved_count = 0
        pending_count = 0
        expired_count = 0
        
        # For chart calculations
        from collections import defaultdict
        monthly_trend = defaultdict(int)
        region_count = defaultdict(int)
        status_breakdown = defaultdict(int)
        
        for doc in docs:
            data = doc.to_dict()
            
            # National only sees approved permits from Regional
            status = data.get('status', 'pending').lower()
            
            # Only include if approved by regional
            if status == 'approved':
                total_count += 1
                
                # Determine national status
                national_status = data.get('nationalStatus', 'pending').lower()
                if national_status == 'approved':
                    approved_count += 1
                elif national_status == 'expired':
                    expired_count += 1
                else:
                    pending_count += 1
                
                # Count by status for chart
                status_breakdown[national_status] += 1
                
                # Format the permit data
                created_at = data.get('createdAt')
                date_obj = None
                if created_at:
                    # Handle Firestore timestamp
                    if isinstance(created_at, str):
                        try:
                            date_obj = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                            date_filed = date_obj.strftime('%b %d, %Y')
                        except:
                            date_filed = created_at
                    elif hasattr(created_at, 'strftime'):
                        date_obj = created_at
                        date_filed = created_at.strftime('%b %d, %Y')
                    else:
                        date_filed = 'N/A'
                else:
                    date_filed = 'N/A'
                
                # Calculate monthly trend for last 6 months
                if date_obj:
                    month_key = date_obj.strftime('%Y-%m')
                    monthly_trend[month_key] += 1
                
                # Get form data
                form_data = data.get('formData', {})
                
                # Extract permit details
                full_name = form_data.get('fullName', 'N/A')
                municipality = form_data.get('municipality', 'N/A')
                
                # Extract location from form data
                region = form_data.get('region', 'N/A')
                location = f"{region} / {municipality}"
                
                # Count by region
                if region and region != 'N/A':
                    region_count[region] += 1
                
                # Map applicationType to classification
                app_type = data.get('applicationType', 'N/A')
                classification_map = {
                    'farm-visit': 'Farm Permit',
                    'fishery-permit': 'Fishery License',
                    'livestock': 'Livestock Permit',
                    'forest': 'Forestry Permit',
                    'wildlife': 'Wildlife Permit',
                    'environment': 'ECC Permit'
                }
                classification = classification_map.get(app_type.lower(), app_type.upper())
                
                # Get issue and expiry dates
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
                    'issue_date': issue_date,
                    'expiry_date': expiry_date
                })
        
        # Sort by most recent first
        permits.sort(key=lambda x: x['date_filed'], reverse=True)
        
        # Prepare chart data - last 6 months
        import calendar
        current_date = datetime.now()
        last_6_months = []
        trend_data = []
        
        for i in range(5, -1, -1):
            # Calculate month and year
            target_month = current_date.month - i
            target_year = current_date.year
            
            # Handle negative months (previous year)
            while target_month <= 0:
                target_month += 12
                target_year -= 1
            
            month_key = f"{target_year}-{target_month:02d}"
            month_label = calendar.month_abbr[target_month]
            last_6_months.append(month_label)
            trend_data.append(monthly_trend.get(month_key, 0))
        
        # Top 5 regions by volume
        top_regions = sorted(region_count.items(), key=lambda x: x[1], reverse=True)[:5]
        region_labels = [item[0] for item in top_regions] if top_regions else ['N/A']
        region_counts = [item[1] for item in top_regions] if top_regions else [0]
        
        # Status breakdown
        status_labels = ['Approved', 'Pending', 'Expired']
        status_data = [
            status_breakdown.get('approved', 0),
            status_breakdown.get('pending', 0),
            status_breakdown.get('expired', 0)
        ]
        
        return render_template('national/licensing-permit-national.html',
                             permits=permits,
                             total_count=total_count,
                             approved_count=approved_count,
                             pending_count=pending_count,
                             expired_count=expired_count,
                             # Chart data
                             trend_labels=last_6_months,
                             trend_data=trend_data,
                             region_labels=region_labels,
                             region_counts=region_counts,
                             status_labels=status_labels,
                             status_data=status_data)
    except Exception as e:
        print(f"Error fetching permits: {str(e)}")
        import traceback
        traceback.print_exc()
        # Return empty data on error
        return render_template('national/licensing-permit-national.html',
                             permits=[],
                             total_count=0,
                             approved_count=0,
                             pending_count=0,
                             expired_count=0,
                             trend_labels=['S', 'O', 'N', 'D', 'J', 'F'],
                             trend_data=[0, 0, 0, 0, 0, 0],
                             region_labels=['N/A'],
                             region_counts=[0],
                             status_labels=['Approved', 'Pending', 'Expired'],
                             status_data=[0, 0, 0])

@bp.route('/service-national')
def service_national_view():
    try:
        db = get_firestore_db()
        
        # Fetch service requests that Regional has approved OR marked for review by National
        service_requests_ref = db.collection('service_requests')
        docs = service_requests_ref.stream()
        
        service_requests = []
        total_count = 0
        completed_count = 0
        pending_count = 0
        rejected_count = 0
        
        # For chart calculations
        from collections import defaultdict
        monthly_trend = defaultdict(int)
        service_type_count = defaultdict(int)
        status_breakdown = defaultdict(int)
        
        for doc in docs:
            data = doc.to_dict()
            
            # National sees approved AND to review from Regional (status: approved, to review, or review)
            status = data.get('status', 'pending').lower()
            
            # Only include if approved or to review by regional
            if status in ['approved', 'to review', 'review']:
                total_count += 1
                
                # National status determines display and counts
                national_status = data.get('nationalStatus', 'pending').lower()
                if national_status == 'approved':
                    completed_count += 1
                elif national_status == 'rejected':
                    rejected_count += 1
                else:
                    pending_count += 1
                
                # Format the service request data
                created_at = data.get('createdAt')
                date_obj = None
                if created_at:
                    # Handle string dates or timestamps
                    if isinstance(created_at, str):
                        try:
                            date_obj = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                            date_filed = date_obj.strftime('%b %d, %Y')
                        except:
                            date_filed = created_at
                    elif hasattr(created_at, 'strftime'):
                        date_obj = created_at
                        date_filed = created_at.strftime('%b %d, %Y')
                    else:
                        date_filed = 'N/A'
                else:
                    date_filed = 'N/A'
                
                # Calculate monthly trend for last 6 months
                if date_obj:
                    month_key = date_obj.strftime('%Y-%m')
                    monthly_trend[month_key] += 1
                
                # Extract service request details
                service_type = data.get('serviceType', 'N/A')
                user_email = data.get('userEmail', 'N/A')
                user_id = data.get('userId', 'N/A')
                
                # Count by service type
                service_type_count[service_type] += 1
                
                # Count by status (for breakdown) - National only has approved/rejected/pending
                if national_status in ['approved', 'rejected']:
                    status_breakdown[national_status] += 1
                else:
                    status_breakdown['pending'] += 1
                
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
                    'status': national_status,  # Use nationalStatus for display
                    'regional_status': status,  # Keep regional status for reference
                    'user_email': user_email,
                    'approved_by_regional': approved_by_regional,
                    'approval_date': approval_date
                })
        
        # Sort by most recent first
        service_requests.sort(key=lambda x: x['date_filed'], reverse=True)
        
        # Prepare chart data - last 6 months
        import calendar
        current_date = datetime.now()
        last_6_months = []
        trend_data = []
        
        for i in range(5, -1, -1):
            # Calculate month and year
            target_month = current_date.month - i
            target_year = current_date.year
            
            # Handle negative months (previous year)
            while target_month <= 0:
                target_month += 12
                target_year -= 1
            
            month_key = f"{target_year}-{target_month:02d}"
            month_label = calendar.month_abbr[target_month]
            last_6_months.append(month_label)
            trend_data.append(monthly_trend.get(month_key, 0))
        
        # Top 5 service types
        top_service_types = sorted(service_type_count.items(), key=lambda x: x[1], reverse=True)[:5]
        service_labels = [item[0][:10] for item in top_service_types] if top_service_types else ['N/A']
        service_counts = [item[1] for item in top_service_types] if top_service_types else [0]
        
        # Status breakdown - National only has Approved, Pending, Rejected (no "Review")
        status_labels = ['Approved', 'Pending', 'Rejected']
        status_data = [
            status_breakdown.get('approved', 0),
            status_breakdown.get('pending', 0),
            status_breakdown.get('rejected', 0)
        ]
        
        return render_template('national/service-national.html',
                             service_requests=service_requests,
                             total_count=total_count,
                             completed_count=completed_count,
                             pending_count=pending_count,
                             rejected_count=rejected_count,
                             # Chart data
                             trend_labels=last_6_months,
                             trend_data=trend_data,
                             service_labels=service_labels,
                             service_counts=service_counts,
                             status_labels=status_labels,
                             status_data=status_data)
    except Exception as e:
        print(f"Error fetching service requests: {str(e)}")
        import traceback
        traceback.print_exc()
        # Return empty data on error
        return render_template('national/service-national.html',
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
                             status_data=[0, 0, 0])

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
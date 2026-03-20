"""
Projects Management Storage Module
Handles creation, approval workflow, and retrieval of projects across admin levels.

Workflow:
- National Admin: Creates project → Auto-approved → Visible to all regions/municipalities
- Regional Admin: Creates project → Pending national approval → Visible to assigned region
- Municipal Admin: Creates project → Pending regional review → Regional approves → National approves → Active
"""

from firebase_admin import firestore
from datetime import datetime, timedelta
## Use only firestore.SERVER_TIMESTAMP from firebase_admin
import logging

db = firestore.client()
logger = logging.getLogger(__name__)


def create_project_national(name, description, region, municipality, start_date, created_by_email, barangay=''):
    """
    National admin creates project - direct creation with auto-approval
    Project is immediately visible to all admins
    """
    try:
        project_data = {
            'name': name,
            'description': description,
            'region': region,
            'municipality': municipality,
            'barangay': barangay,
            'start_date': start_date,
            'created_by': created_by_email,
            'created_by_role': 'national_admin',
            'created_at': firestore.SERVER_TIMESTAMP,
            'status': 'active',
            'status_level': 'active',
            'approval_chain': [],
        }
        
        doc_ref = db.collection('projects').document()
        doc_ref.set(project_data)
        
        logger.info(f"[PROJECT_CREATION] National admin created project: {name} ({region})")
        return {'success': True, 'project_id': doc_ref.id, 'project': project_data}
        
    except Exception as e:
        logger.error(f"[PROJECT_ERROR] Failed to create national project: {e}")
        return {'success': False, 'error': str(e)}


def create_project_regional(name, description, region, municipality, start_date, created_by_email, barangay=''):
    """
    Regional admin creates project - pending national approval
    Project visible to: regional admin (creator), national admin
    """
    try:
        project_data = {
            'name': name,
            'description': description,
            'region': region,
            'municipality': municipality,
            'barangay': barangay,
            'start_date': start_date,
            'created_by': created_by_email,
            'created_by_role': 'regional_admin',
            'created_at': firestore.SERVER_TIMESTAMP,
            'status': 'pending_national_approval',
            'status_level': 'pending_national_approval',
            'approval_chain': [
                {
                    'role': 'national',
                    'status': 'pending',
                    'requested_at': firestore.SERVER_TIMESTAMP,
                    'reviewer': None,
                    'reviewed_at': None,
                    'notes': ''
                }
            ],
        }
        
        doc_ref = db.collection('projects').document()
        doc_ref.set(project_data)
        
        logger.info(f"[PROJECT_CREATION] Regional admin created project awaiting national approval: {name}")
        return {'success': True, 'project_id': doc_ref.id, 'project': project_data}
        
    except Exception as e:
        logger.error(f"[PROJECT_ERROR] Failed to create regional project: {e}")
        return {'success': False, 'error': str(e)}


def create_project_municipal(name, description, region, municipality, start_date, created_by_email, barangay=''):
    """
    Municipal admin creates project - requires regional review, then national approval
    Project visible to: municipal admin (creator), regional admin (assigned to region), national admin
    """
    try:
        project_data = {
            'name': name,
            'description': description,
            'region': region,
            'municipality': municipality,
            'barangay': barangay,
            'start_date': start_date,
            'created_by': created_by_email,
            'created_by_role': 'municipal_admin',
            'created_at': firestore.SERVER_TIMESTAMP,
            'status': 'pending_regional_approval',
            'status_level': 'pending_regional_approval',
            'approval_chain': [
                {
                    'role': 'regional',
                    'status': 'pending',
                    'requested_at': firestore.SERVER_TIMESTAMP,
                    'reviewer': None,
                    'reviewed_at': None,
                    'notes': ''
                },
                {
                    'role': 'national',
                    'status': 'pending',
                    'requested_at': firestore.SERVER_TIMESTAMP,
                    'reviewer': None,
                    'reviewed_at': None,
                    'notes': ''
                }
            ],
        }
        
        doc_ref = db.collection('projects').document()
        doc_ref.set(project_data)
        
        logger.info(f"[PROJECT_CREATION] Municipal admin created project awaiting regional review: {name}")
        return {'success': True, 'project_id': doc_ref.id, 'project': project_data}
        
    except Exception as e:
        logger.error(f"[PROJECT_ERROR] Failed to create municipal project: {e}")
        return {'success': False, 'error': str(e)}


def approve_project_regional(project_id, reviewer_email, notes=''):
    """
    Regional admin approves a municipal project
    Status moves: pending_regional_approval → pending_national_approval
    """
    try:
        project_ref = db.collection('projects').document(project_id)
        project = project_ref.get()
        
        if not project.exists:
            return {'success': False, 'error': 'Project not found'}
        
        project_data = project.to_dict()
        
        # Only municipal-created projects can be reviewed by regional
        if project_data.get('status') != 'pending_regional_approval':
            return {'success': False, 'error': 'Project is not pending regional approval'}
        
        # Update approval chain
        approval_chain = project_data.get('approval_chain', [])
        if approval_chain and approval_chain[0]['role'] == 'regional':
            approval_chain[0]['status'] = 'approved'
            approval_chain[0]['reviewer'] = reviewer_email
            approval_chain[0]['reviewed_at'] = firestore.SERVER_TIMESTAMP
            approval_chain[0]['notes'] = notes
        
        # Update project status
        project_ref.update({
            'status': 'pending_national_approval',
            'status_level': 'pending_national_approval',
            'approval_chain': approval_chain
        })
        
        logger.info(f"[PROJECT_APPROVAL] Regional admin approved project {project_id} for national review")
        return {'success': True, 'message': 'Project forwarded to National Admin for final approval'}
        
    except Exception as e:
        logger.error(f"[PROJECT_ERROR] Failed to approve regional project: {e}")
        return {'success': False, 'error': str(e)}


def reject_project_regional(project_id, reviewer_email, notes=''):
    """
    Regional admin rejects a municipal project
    Status moves: pending_regional_approval → rejected
    """
    try:
        project_ref = db.collection('projects').document(project_id)
        project = project_ref.get()
        
        if not project.exists:
            return {'success': False, 'error': 'Project not found'}
        
        project_data = project.to_dict()
        
        if project_data.get('status') != 'pending_regional_approval':
            return {'success': False, 'error': 'Project is not pending regional approval'}
        
        # Update approval chain
        approval_chain = project_data.get('approval_chain', [])
        if approval_chain and approval_chain[0]['role'] == 'regional':
            approval_chain[0]['status'] = 'rejected'
            approval_chain[0]['reviewer'] = reviewer_email
            approval_chain[0]['reviewed_at'] = firestore.SERVER_TIMESTAMP
            approval_chain[0]['notes'] = notes
        
        project_ref.update({
            'status': 'rejected',
            'status_level': 'rejected',
            'approval_chain': approval_chain
        })
        
        logger.info(f"[PROJECT_REJECTION] Regional admin rejected project {project_id}")
        return {'success': True, 'message': 'Project rejected and sent back to municipal admin'}
        
    except Exception as e:
        logger.error(f"[PROJECT_ERROR] Failed to reject regional project: {e}")
        return {'success': False, 'error': str(e)}


def approve_project_national(project_id, reviewer_email, notes=''):
    """
    National admin approves a project
    Regional project: pending_national_approval → active
    Municipal project (after regional ok): pending_national_approval → active
    """
    try:
        project_ref = db.collection('projects').document(project_id)
        project = project_ref.get()
        
        if not project.exists:
            return {'success': False, 'error': 'Project not found'}
        
        project_data = project.to_dict()
        
        if project_data.get('status') != 'pending_national_approval':
            return {'success': False, 'error': 'Project is not pending national approval'}
        
        # Update approval chain - find national role
        approval_chain = project_data.get('approval_chain', [])
        for approval in approval_chain:
            if approval['role'] == 'national':
                approval['status'] = 'approved'
                approval['reviewer'] = reviewer_email
                approval['reviewed_at'] = firestore.SERVER_TIMESTAMP
                approval['notes'] = notes
        
        project_ref.update({
            'status': 'active',
            'status_level': 'active',
            'approval_chain': approval_chain
        })
        
        logger.info(f"[PROJECT_APPROVAL] National admin approved project {project_id} - now active")
        return {'success': True, 'message': 'Project approved and is now active'}
        
    except Exception as e:
        logger.error(f"[PROJECT_ERROR] Failed to approve national project: {e}")
        return {'success': False, 'error': str(e)}


def reject_project_national(project_id, reviewer_email, notes=''):
    """
    National admin rejects a project
    Status moves to: rejected
    """
    try:
        project_ref = db.collection('projects').document(project_id)
        project = project_ref.get()
        
        if not project.exists:
            return {'success': False, 'error': 'Project not found'}
        
        project_data = project.to_dict()
        
        if project_data.get('status') != 'pending_national_approval':
            return {'success': False, 'error': 'Project is not pending national approval'}
        
        # Update approval chain
        approval_chain = project_data.get('approval_chain', [])
        for approval in approval_chain:
            if approval['role'] == 'national':
                approval['status'] = 'rejected'
                approval['reviewer'] = reviewer_email
                approval['reviewed_at'] = firestore.SERVER_TIMESTAMP
                approval['notes'] = notes
        
        project_ref.update({
            'status': 'rejected',
            'status_level': 'rejected',
            'approval_chain': approval_chain
        })
        
        logger.info(f"[PROJECT_REJECTION] National admin rejected project {project_id}")
        return {'success': True, 'message': 'Project rejected'}
        
    except Exception as e:
        logger.error(f"[PROJECT_ERROR] Failed to reject national project: {e}")
        return {'success': False, 'error': str(e)}


def get_projects_national():
    """
    National admin sees all projects
    """
    try:
        projects = []
        for doc in db.collection('projects').where('status', '!=', 'archived').stream():
            item = doc.to_dict()
            item['id'] = doc.id
            projects.append(item)
        
        return projects
    except Exception as e:
        logger.error(f"[PROJECT_ERROR] Failed to fetch national projects: {e}")
        return []


def get_projects_regional(user_region):
    """
    Regional admin sees:
    - All active projects in their region
    - All pending projects created by regional admins in their region
    - All pending projects created by municipal admins in their region municipalities
    """
    try:
        projects = []
        
        # Active projects in this region
        active_query = db.collection('projects').where('region', '==', user_region).where('status', '==', 'active').stream()
        for doc in active_query:
            item = doc.to_dict()
            item['id'] = doc.id
            projects.append(item)
        
        # Pending regional projects created by regional admin in this region
        pending_regional = db.collection('projects').where('region', '==', user_region).where('created_by_role', '==', 'regional_admin').where('status', '==', 'pending_national_approval').stream()
        for doc in pending_regional:
            item = doc.to_dict()
            item['id'] = doc.id
            projects.append(item)
        
        # Pending municipal projects (need regional review) in this region
        pending_municipal = db.collection('projects').where('region', '==', user_region).where('created_by_role', '==', 'municipal_admin').where('status', '==', 'pending_regional_approval').stream()
        for doc in pending_municipal:
            item = doc.to_dict()
            item['id'] = doc.id
            projects.append(item)
        
        return projects
    except Exception as e:
        logger.error(f"[PROJECT_ERROR] Failed to fetch regional projects: {e}")
        return []


def get_projects_municipal(municipality, region):
    """
    Municipal admin sees:
    - All active projects in their municipality
    - All active projects in their region
    - All projects they created (regardless of status)
    - Projects pending regional/national approval created by admins in their region
    """
    try:
        projects = []
        
        # Active projects in this municipality
        active_mun = db.collection('projects').where('municipality', '==', municipality).where('status', '==', 'active').stream()
        for doc in active_mun:
            item = doc.to_dict()
            item['id'] = doc.id
            projects.append(item)
        
        # Active projects in this region
        active_region = db.collection('projects').where('region', '==', region).where('status', '==', 'active').stream()
        for doc in active_region:
            item = doc.to_dict()
            item['id'] = doc.id
            # Avoid duplicates
            if item['id'] not in [p.get('id') for p in projects]:
                projects.append(item)
        
        # All projects created by this user
        my_projects = db.collection('projects').where('created_by', '==', municipality).stream()
        for doc in my_projects:
            item = doc.to_dict()
            item['id'] = doc.id
            if item['id'] not in [p.get('id') for p in projects]:
                projects.append(item)
        
        return projects
    except Exception as e:
        logger.error(f"[PROJECT_ERROR] Failed to fetch municipal projects: {e}")
        return []


def get_projects_for_approval(role, user_region=None):
    """
    Get projects pending approval for a specific role
    - role = 'regional': Projects pending regional review (created by municipal admin)
    - role = 'national': Projects pending national approval (created by regional or approved by regional)
    """
    try:
        projects = []
        
        if role == 'regional' and user_region:
            # Projects pending regional approval in this region
            query = db.collection('projects').where('status', '==', 'pending_regional_approval').where('region', '==', user_region).stream()
            for doc in query:
                item = doc.to_dict()
                item['id'] = doc.id
                projects.append(item)
        
        elif role == 'national':
            # All projects pending national approval
            query = db.collection('projects').where('status', '==', 'pending_national_approval').stream()
            for doc in query:
                item = doc.to_dict()
                item['id'] = doc.id
                projects.append(item)
        
        return projects
    except Exception as e:
        logger.error(f"[PROJECT_ERROR] Failed to fetch projects for approval: {e}")
        return []


def get_project_by_id(project_id):
    """
    Get a single project by ID
    """
    try:
        doc = db.collection('projects').document(project_id).get()
        if doc.exists:
            item = doc.to_dict()
            item['id'] = doc.id
            return item
        return None
    except Exception as e:
        logger.error(f"[PROJECT_ERROR] Failed to fetch project {project_id}: {e}")
        return None


def update_project(project_id, update_data):
    """
    Update project details (for active projects only)
    """
    try:
        project_ref = db.collection('projects').document(project_id)
        project = project_ref.get()
        
        if not project.exists:
            return {'success': False, 'error': 'Project not found'}
        
        project_data = project.to_dict()
        
        # Can only edit active projects
        if project_data.get('status') != 'active':
            return {'success': False, 'error': 'Can only edit active projects'}
        
        project_ref.update(update_data)
        logger.info(f"[PROJECT_UPDATE] Project {project_id} updated")
        return {'success': True, 'message': 'Project updated'}
        
    except Exception as e:
        logger.error(f"[PROJECT_ERROR] Failed to update project: {e}")
        return {'success': False, 'error': str(e)}


def archive_project(project_id):
    """
    Archive a project (soft delete)
    """
    try:
        project_ref = db.collection('projects').document(project_id)
        project_ref.update({'status': 'archived', 'archived_at': firestore.SERVER_TIMESTAMP})
        logger.info(f"[PROJECT_ARCHIVE] Project {project_id} archived")
        return {'success': True, 'message': 'Project archived'}
        
    except Exception as e:
        logger.error(f"[PROJECT_ERROR] Failed to archive project: {e}")
        return {'success': False, 'error': str(e)}

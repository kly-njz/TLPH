"""
Service Request Handlers for Compensation Services
Handles form submission, file uploads, and data storage for:
- Typhoon Damage Compensation
- Pest Damage Compensation
"""

import uuid
from datetime import datetime
from firebase_config import db

class CompensationServiceHandler:
    """
    Handler for managing compensation service requests
    """

    @staticmethod
    def create_request(user_id: str, service_type: str, form_data: dict, attachments: list) -> dict:
        """
        Creates a new compensation service request
        
        Args:
            user_id: Authenticated user ID
            service_type: 'Typhoon Damage Compensation' or 'Pest Damage Compensation'
            form_data: Dictionary of form fields
            attachments: List of file dictionaries with 'url' and 'name'
        
        Returns:
            Dictionary with request_id and success status
        """
        try:
            request_id = str(uuid.uuid4())
            
            # Build request document
            request_doc = {
                'id': request_id,
                'userId': user_id,
                'serviceType': service_type,
                'submittedAt': datetime.now().isoformat(),
                'status': 'pending',
                'supportingDocuments': attachments or [],
            }
            
            # Add all form fields
            request_doc.update(form_data)
            
            # Store in Firestore
            db.collection('serviceRequests').document(request_id).set(request_doc)
            
            return {
                'success': True,
                'requestId': request_id,
                'message': f'{service_type} request submitted successfully'
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    @staticmethod
    def get_user_requests(user_id: str, service_type: str = None) -> list:
        """
        Retrieves all compensation service requests for a user
        
        Args:
            user_id: User ID
            service_type: Optional filter by service type
        
        Returns:
            List of request documents
        """
        try:
            query = db.collection('serviceRequests').where('userId', '==', user_id)
            
            if service_type:
                query = query.where('serviceType', '==', service_type)
            
            docs = query.order_by('submittedAt', direction='DESCENDING').stream()
            
            return [doc.to_dict() for doc in docs]
        except Exception as e:
            print(f'Error retrieving requests: {str(e)}')
            return []

    @staticmethod
    def get_request_by_id(user_id: str, request_id: str) -> dict:
        """
        Retrieves a specific service request if user owns it
        
        Args:
            user_id: User ID
            request_id: Request ID
        
        Returns:
            Request document or None if not found/unauthorized
        """
        try:
            doc = db.collection('serviceRequests').document(request_id).get()
            
            if not doc.exists:
                return None
            
            data = doc.to_dict()
            
            # Verify ownership
            if data.get('userId') != user_id:
                return None
            
            return data
        except Exception as e:
            print(f'Error retrieving request: {str(e)}')
            return None

    @staticmethod
    def update_request_status(user_id: str, request_id: str, status: str) -> bool:
        """
        Updates the status of a service request (admin/staff only)
        
        Args:
            user_id: User ID
            request_id: Request ID
            status: New status ('pending', 'approved', 'rejected', 'archived')
        
        Returns:
            True if successful, False otherwise
        """
        try:
            doc = db.collection('serviceRequests').document(request_id).get()
            
            if not doc.exists:
                return False
            
            data = doc.to_dict()
            
            # Verify ownership
            if data.get('userId') != user_id:
                return False
            
            db.collection('serviceRequests').document(request_id).update({
                'status': status,
                'updatedAt': datetime.now().isoformat()
            })
            
            return True
        except Exception as e:
            print(f'Error updating request: {str(e)}')
            return False

    @staticmethod
    def delete_request(user_id: str, request_id: str) -> bool:
        """
        Deletes a service request (user can only delete their own)
        
        Args:
            user_id: User ID
            request_id: Request ID
        
        Returns:
            True if successful, False otherwise
        """
        try:
            doc = db.collection('serviceRequests').document(request_id).get()
            
            if not doc.exists:
                return False
            
            data = doc.to_dict()
            
            # Verify ownership
            if data.get('userId') != user_id:
                return False
            
            # Only allow deletion of pending requests
            if data.get('status') != 'pending':
                return False
            
            db.collection('serviceRequests').document(request_id).delete()
            
            return True
        except Exception as e:
            print(f'Error deleting request: {str(e)}')
            return False

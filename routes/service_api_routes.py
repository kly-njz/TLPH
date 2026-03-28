"""
Service request API endpoints for handling compensation service requests submission and retrieval
"""
from flask import Blueprint, request, jsonify, session
from firebase_auth_middleware import role_required
from firebase_config import db
from datetime import datetime
import uuid

bp = Blueprint('service_api', __name__, url_prefix='/api/service')
SERVICE_REQUESTS_COLLECTION = 'service_requests'

@bp.route('/compensation/submit', methods=['POST'])
@role_required('user')
def submit_compensation_request():
    """
    Handles submission of compensation service requests (Typhoon and Pest Damage)
    Expected form data: serviceType, formData (dict), files (list of uploaded files)
    """
    try:
        # Get user from session (set by @role_required decorator)
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'error': 'Unauthorized'}), 401

        # Parse form data
        service_type = request.form.get('serviceType')
        print(f"\n===== COMPENSATION SUBMIT REQUEST =====")
        print(f"User ID: {user_id}")
        print(f"Service Type: {service_type}")
        print(f"Request Method: {request.method}")
        print(f"Request Content-Type: {request.content_type}")
        print(f"Form keys: {list(request.form.keys())}")
        print(f"Files keys: {list(request.files.keys())}")
        print(f"===== END REQUEST INFO =====\n")
        
        if not service_type:
            return jsonify({'error': 'Service type is required'}), 400

        # Create service request document
        request_id = str(uuid.uuid4())
        submission_data = {
            'id': request_id,
            'userId': user_id,
            'serviceType': service_type,
            'submittedAt': datetime.now().isoformat(),
            'createdAt': datetime.now(),
            'status': 'pending',  # pending, approved, rejected
            'supportingDocuments': []
        }

        # Add form fields
        form_fields = {
            'typhoonName', 'areaAffected', 'province', 'municipality', 'barangay',
            'occurrenceTime', 'cropSpecies', 'damageType', 'narrative',
            'farmerIdNumber', 'costOfDamage', 'farmLatitude', 'farmLongitude', 'farmAddress', 'googlePinLocation',
            'pestType', 'areaDamaged', 'lossValue', 'dateObserved', 'lastSpray'
        }

        for field in form_fields:
            value = request.form.get(field)
            if value is not None:
                submission_data[field] = value

        # Handle file uploads
        files_to_upload = request.files.getlist('supportingFiles')
        print(f'🔵 [COMPENSATION] Files received: {len(files_to_upload)} file(s)')
        print(f'🔵 [COMPENSATION] Files list: {request.files.keys()}')
        
        if files_to_upload:
            from routes.api_routes import _upload_to_cloudinary
            for file in files_to_upload:
                if file and file.filename:
                    print(f'📤 [COMPENSATION] Uploading file: {file.filename} (size: {file.content_length})')
                    try:
                        web_url = _upload_to_cloudinary(file, f'service-requests/{service_type}/{user_id}')
                        print(f'📥 [COMPENSATION] Upload result: {web_url}')
                        
                        if web_url:
                            submission_data['supportingDocuments'].append({
                                'url': web_url,
                                'name': file.filename
                            })
                            print(f'✅ [COMPENSATION] File stored: {file.filename} -> {web_url}')
                        else:
                            print(f'❌ [COMPENSATION] Cloudinary returned None for {file.filename}')
                            # Fallback: store filename with error indicator
                            submission_data['supportingDocuments'].append({
                                'url': 'ERROR_UPLOAD_FAILED',
                                'name': file.filename,
                                'error': 'Cloudinary upload failed'
                            })
                    except Exception as file_error:
                        print(f'❌ [COMPENSATION] Exception uploading {file.filename}: {str(file_error)}')
                        submission_data['supportingDocuments'].append({
                            'url': 'ERROR_EXCEPTION',
                            'name': file.filename,
                            'error': str(file_error)
                        })
        
        print(f'🔵 [COMPENSATION] Final supportingDocuments: {len(submission_data["supportingDocuments"])} docs')
        for doc in submission_data['supportingDocuments']:
            print(f'  - {doc.get("name")}: {doc.get("url")}')

        # Store in Firestore
        db.collection(SERVICE_REQUESTS_COLLECTION).document(request_id).set(submission_data)

        return jsonify({
            'success': True,
            'requestId': request_id,
            'message': f'{service_type} request submitted successfully'
        }), 200

    except Exception as e:
        print(f'Error submitting service request: {str(e)}')
        import traceback
        traceback.print_exc()
        return jsonify({'error': 'Failed to submit request', 'details': str(e)}), 500


@bp.route('/compensation/<request_id>', methods=['GET'])
@role_required('user')
def get_compensation_request(request_id):
    """
    Retrieves a specific compensation service request for the current user
    """
    try:
        # Get user from session (set by @role_required decorator)
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'error': 'Unauthorized'}), 401

        doc = db.collection(SERVICE_REQUESTS_COLLECTION).document(request_id).get()
        if not doc.exists:
            # Backward compatibility for any records saved in legacy collection name
            doc = db.collection('serviceRequests').document(request_id).get()
        
        if not doc.exists:
            return jsonify({'error': 'Request not found'}), 404

        data = doc.to_dict()
        
        # Verify ownership
        if data.get('userId') != user_id:
            return jsonify({'error': 'Unauthorized'}), 403

        return jsonify(data), 200

    except Exception as e:
        print(f'Error retrieving service request: {str(e)}')
        return jsonify({'error': 'Failed to retrieve request', 'details': str(e)}), 500


@bp.route('/compensation/list', methods=['GET'])
@role_required('user')
def list_compensation_requests():
    """
    Lists all compensation service requests for the current user
    """
    try:
        # Get user from session (set by @role_required decorator)
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'error': 'Unauthorized'}), 401

        service_type = request.args.get('serviceType')  # Optional filter
        
        query = db.collection(SERVICE_REQUESTS_COLLECTION).where('userId', '==', user_id)
        
        if service_type:
            query = query.where('serviceType', '==', service_type)
        
        docs = query.order_by('submittedAt', direction='DESCENDING').stream()
        
        requests_list = []
        for doc in docs:
            requests_list.append(doc.to_dict())

        return jsonify({
            'requests': requests_list,
            'count': len(requests_list)
        }), 200

    except Exception as e:
        print(f'Error listing service requests: {str(e)}')
        return jsonify({'error': 'Failed to retrieve requests', 'details': str(e)}), 500

from flask import Blueprint, request, jsonify, render_template, send_file
from config import Config
import requests
from datetime import datetime
import base64
import transaction_storage
from io import BytesIO
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from firebase_auth_middleware import firebase_auth_required
from reportlab.lib import colors
from reportlab.lib.units import inch

import uuid

bp = Blueprint('payments', __name__, url_prefix='/api/payments')

# Xendit API Base URL
XENDIT_BASE_URL = 'https://api.xendit.co'

def get_xendit_auth_header():
    """Generate Xendit API authentication header"""
    if not Config.XENDIT_API_KEY:
        return None
    api_key_bytes = (Config.XENDIT_API_KEY + ':').encode('utf-8')
    encoded = base64.b64encode(api_key_bytes).decode('utf-8')
    return f'Basic {encoded}'

@bp.route('/create-invoice', methods=['POST'])
def create_invoice():
    """Create a Xendit invoice for license/permit payments"""
    try:
        data = request.get_json(silent=True) or {}
        auth_header = get_xendit_auth_header()
        
        if not auth_header:
            return jsonify({
                'status': 'error',
                'message': 'Xendit API key not configured'
            }), 400
        
        # Basic payload validation before calling Xendit
        raw_amount = data.get('amount')
        try:
            amount = int(raw_amount)
        except (TypeError, ValueError):
            amount = 0

        if amount <= 0:
            return jsonify({
                'status': 'error',
                'message': 'Amount must be greater than 0'
            }), 400

        email = (data.get('email') or '').strip()
        if email and '@' not in email:
            return jsonify({
                'status': 'error',
                'message': 'Invalid payer email'
            }), 400

        # Generate short unique external_id (Xendit limit: 40 chars)
        external_id = f"svc-{uuid.uuid4().hex[:16]}"
        
        invoice_payload = {
            'external_id': external_id,
            'amount': amount,
            'description': data.get('description', 'DENR License/Permit Payment'),
            'success_redirect_url': data.get('success_url', 'http://localhost:5000/payment-success'),
            'failure_redirect_url': data.get('failure_url', 'http://localhost:5000/payment-failed'),
            'items': [
                {
                    'name': data.get('item_name', 'License/Permit'),
                    'quantity': 1,
                    'price': amount
                }
            ]
        }

        if email:
            invoice_payload['payer_email'] = email
        
        # Add customer info if provided
        # Only include customer if we have at least one field
        customer = {}
        if data.get('first_name'):
            customer['given_names'] = data.get('first_name')
        if data.get('last_name'):
            customer['surname'] = data.get('last_name')
        if email:
            customer['email'] = email
        if data.get('phone'):
            customer['mobile_number'] = data.get('phone')
        
        if customer:
            invoice_payload['customer'] = customer
        
        # Create invoice via Xendit API
        headers = {
            'Authorization': auth_header,
            'Content-Type': 'application/json'
        }
        
        response = requests.post(
            f'{XENDIT_BASE_URL}/v2/invoices',
            json=invoice_payload,
            headers=headers,
            timeout=10
        )
        
        if response.status_code in [200, 201]:
            invoice = response.json()
            
            # Save transaction record with userId
            transaction_storage.add_transaction(
                user_email=email,
                external_id=external_id,
                invoice_id=invoice.get('id'),
                amount=amount,
                item_name=data.get('item_name', 'License/Permit'),
                description=data.get('description', 'DENR License/Permit Payment'),
                status='Pending',
                user_id=data.get('user_id')
            )
            
            return jsonify({
                'status': 'success',
                'invoice_id': invoice.get('id'),
                'invoice_url': invoice.get('invoice_url'),
                'amount': invoice.get('amount'),
                'external_id': invoice.get('external_id')
            }), 201
        else:
            try:
                error_body = response.json()
            except ValueError:
                error_body = {'raw': response.text}
            return jsonify({
                'status': 'error',
                'message': f"Xendit API error: {response.status_code}",
                'details': error_body
            }), response.status_code
        
    except requests.exceptions.RequestException as e:
        return jsonify({
            'status': 'error',
            'message': f'Request failed: {str(e)}'
        }), 400
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 400


@bp.route('/check-invoice/<invoice_id>', methods=['GET'])
def check_invoice_status(invoice_id):
    """Check the status of a Xendit invoice"""
    try:
        auth_header = get_xendit_auth_header()
        
        if not auth_header:
            return jsonify({
                'status': 'error',
                'message': 'Xendit API key not configured'
            }), 400
        
        headers = {
            'Authorization': auth_header,
            'Content-Type': 'application/json'
        }
        
        response = requests.get(
            f'{XENDIT_BASE_URL}/v2/invoices/{invoice_id}',
            headers=headers,
            timeout=10
        )
        
        if response.status_code == 200:
            invoice = response.json()
            return jsonify({
                'status': 'success',
                'invoice_id': invoice.get('id'),
                'amount': invoice.get('amount'),
                'paid_amount': invoice.get('paid_amount', 0),
                'payment_status': invoice.get('status'),
                'paid_at': invoice.get('paid_at'),
                'payment_method': invoice.get('payment_method')
            }), 200
        else:
            return jsonify({
                'status': 'error',
                'message': f'Invoice not found or error: {response.status_code}'
            }), response.status_code
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 400


@bp.route('/webhook', methods=['POST'])
def xendit_webhook():
    """Handle Xendit webhook notifications"""
    try:
        data = request.json
        
        # Validate webhook signature (optional but recommended)
        # You should verify the signature using Xendit's verification process
        
        invoice_id = data.get('id')
        status = data.get('status')
        payment_method = data.get('payment_method')
        paid_at = data.get('paid_at')
        
        # Update transaction status
        if invoice_id:
            transaction_storage.update_transaction_status(
                invoice_id=invoice_id,
                status=status,
                payment_method=payment_method,
                paid_at=paid_at
            )
        
        if status == 'PAID':
            # Process successful payment
            external_id = data.get('external_id')
            amount = data.get('amount')
            
            # Additional processing can be done here
            # Example: send email confirmation, update license status, etc.
            
            return jsonify({
                'status': 'success',
                'message': 'Webhook processed'
            }), 200
        
        return jsonify({
            'status': 'success',
            'message': 'Webhook received'
        }), 200
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 400


@bp.route('/payment-form/<service_type>', methods=['GET'])
@firebase_auth_required
def payment_form(service_type):
    """Display payment form for different service types"""
    return render_template('payment-form.html', 
                         service_type=service_type,
                         xendit_public_key=Config.XENDIT_PUBLIC_KEY)


@bp.route('/transactions', methods=['GET'])
def get_transactions():
    """Get transactions for the logged-in user"""
    try:
        # Get user email and userId from query parameters
        user_email = request.args.get('email')
        user_id = request.args.get('userId')
        
        if not user_id and not user_email:
            return jsonify({
                'status': 'error',
                'message': 'User ID or email is required'
            }), 400
        
        transactions = transaction_storage.get_user_transactions(user_email=user_email, user_id=user_id)
        
        # Convert status to display format
        for transaction in transactions:
            status = transaction.get('status', 'Pending')
            if status == 'Approved' or status == 'PAID':
                transaction['display_status'] = 'approved'
            elif status == 'Rejected' or status == 'EXPIRED' or status == 'FAILED':
                transaction['display_status'] = 'rejected'
            elif status == 'Cancelled':
                transaction['display_status'] = 'cancelled'
            else:
                transaction['display_status'] = 'pending'
        
        return jsonify({
            'status': 'success',
            'transactions': transactions
        }), 200
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@bp.route('/statement', methods=['GET'])
def generate_statement():
    """Generate PDF e-statement for user transactions"""
    try:
        user_email = request.args.get('email', '').strip()
        
        if not user_email:
            return jsonify({
                'status': 'error',
                'message': 'Email is required'
            }), 400
        
        # Get transactions
        transactions = transaction_storage.get_user_transactions(user_email)
        
        if not transactions:
            return jsonify({
                'status': 'error',
                'message': 'No transactions found'
            }), 404
        
        # Create PDF in memory
        pdf_buffer = BytesIO()
        doc = SimpleDocTemplate(pdf_buffer, pagesize=letter)
        story = []
        styles = getSampleStyleSheet()
        
        # Title
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=20,
            textColor=colors.HexColor('#111827'),
            spaceAfter=4,
            alignment=1  # Center
        )
        story.append(Paragraph("DENR TRANSACTION STATEMENT", title_style))
        story.append(Paragraph("Department of Environment and Natural Resources", styles['Normal']))
        story.append(Spacer(1, 0.12*inch))
        
        # Statement info
        info_style = ParagraphStyle(
            'InfoStyle',
            parent=styles['Normal'],
            fontSize=9,
            textColor=colors.HexColor('#6b7280')
        )
        story.append(Paragraph(f"<b>Account Email:</b> {user_email}", info_style))
        story.append(Paragraph(f"<b>Statement Date:</b> {datetime.now().strftime('%B %d, %Y')}", info_style))
        story.append(Paragraph(f"<b>Total Transactions:</b> {len(transactions)}", info_style))
        story.append(Spacer(1, 0.15*inch))
        
        # Summary
        story.append(Paragraph("SUMMARY", styles['Heading2']))
        summary_data = [['Status', 'Count', 'Total Amount']]
        
        status_summary = {}
        total_amount = 0
        for t in transactions:
            status = t.get('display_status', 'pending')
            if status not in status_summary:
                status_summary[status] = {'count': 0, 'amount': 0}
            status_summary[status]['count'] += 1
            status_summary[status]['amount'] += t.get('amount', 0)
            total_amount += t.get('amount', 0)
        
        for status in ['approved', 'pending', 'rejected', 'cancelled']:
            if status in status_summary:
                data = status_summary[status]
                summary_data.append([
                    status.upper(),
                    str(data['count']),
                    f"₱{data['amount']:,.2f}"
                ])
        
        summary_data.append(['TOTAL', str(len(transactions)), f"₱{total_amount:,.2f}"])
        
        summary_table = Table(summary_data, colWidths=[1.8*inch, 1.3*inch, 1.8*inch])
        summary_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#fbfcfe')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#6b7280')),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#f3f4f6')),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#e5e7eb')),
        ]))
        story.append(summary_table)
        story.append(Spacer(1, 0.15*inch))
        
        # Transaction details
        story.append(PageBreak())
        story.append(Paragraph("TRANSACTION DETAILS", styles['Heading2']))
        story.append(Spacer(1, 0.12*inch))
        
        # Transaction table
        trans_data = [['Date', 'Application Type', 'Reference', 'Amount', 'Status']]
        
        for t in transactions:
            date_str = t.get('created_at', 'N/A')
            if date_str and date_str != 'N/A':
                try:
                    date_str = datetime.fromisoformat(date_str).strftime('%Y-%m-%d')
                except:
                    pass
            
            trans_data.append([
                date_str,
                t.get('transaction_name', 'Unknown')[:30],  # Truncate long names
                t.get('reference', '')[:25],  # Truncate reference
                f"₱{t.get('amount', 0):,.2f}",
                t.get('display_status', 'pending').upper()
            ])
        
        trans_table = Table(trans_data, colWidths=[1.0*inch, 1.5*inch, 1.2*inch, 1.0*inch, 1.1*inch])
        trans_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#fbfcfe')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#6b7280')),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('ALIGN', (3, 0), (3, -1), 'RIGHT'),  # Amount right-aligned
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#e5e7eb')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f9fafb')]),
        ]))
        story.append(trans_table)
        story.append(Spacer(1, 0.15*inch))
        
        # Footer
        story.append(Spacer(1, 0.2*inch))
        footer_style = ParagraphStyle(
            'FooterStyle',
            parent=styles['Normal'],
            fontSize=8,
            textColor=colors.HexColor('#9ca3af'),
            alignment=1
        )
        story.append(Paragraph("This is an electronic statement generated by DENR Portal", footer_style))
        story.append(Paragraph(f"Generated on: {datetime.now().strftime('%B %d, %Y at %I:%M %p')}", footer_style))
        
        # Build PDF
        doc.build(story)
        pdf_buffer.seek(0)
        
        return send_file(
            pdf_buffer,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=f'DENR-Statement-{datetime.now().strftime("%Y-%m-%d")}.pdf'
        )
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@bp.route('/cancel-transaction', methods=['POST'])
def cancel_transaction():
    """Cancel a pending transaction"""
    try:
        data = request.get_json(silent=True) or {}
        reference = data.get('reference')
        user_email = data.get('user_email')
        
        if not reference:
            return jsonify({
                'status': 'error',
                'message': 'Reference number is required'
            }), 400
        
        if not user_email:
            return jsonify({
                'status': 'error',
                'message': 'User email is required'
            }), 400
        
        result = transaction_storage.cancel_transaction_by_reference(reference, user_email)
        
        if result['success']:
            return jsonify({
                'status': 'success',
                'message': 'Transaction cancelled successfully',
                'transaction': result['transaction']
            }), 200
        else:
            return jsonify({
                'status': 'error',
                'message': result['message']
            }), 400
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@bp.route('/service-payment', methods=['POST'])
def service_payment():
    """Create a payment for service requests"""
    try:
        data = request.get_json(silent=True) or {}
        auth_header = get_xendit_auth_header()
        
        if not auth_header:
            return jsonify({
                'status': 'error',
                'message': 'Xendit API key not configured'
            }), 400
        
        # Extract service payment data
        service_id = data.get('serviceId', '')
        amount = data.get('amount') or 0
        service_type = data.get('serviceType', 'Service Request')
        user_email = (data.get('userEmail') or '').strip()
        
        # Validate required fields
        if not service_id:
            return jsonify({
                'status': 'error',
                'message': 'Service ID is required'
            }), 400
        
        try:
            amount = int(amount) if amount else 0
        except (TypeError, ValueError):
            amount = 0

        if amount <= 0:
            return jsonify({
                'status': 'error',
                'message': 'Amount must be greater than 0'
            }), 400

        if user_email and '@' not in user_email:
            return jsonify({
                'status': 'error',
                'message': 'Invalid payer email'
            }), 400

        # Generate external ID for the invoice
        external_id = f"service-{service_id}-{int(datetime.now().timestamp())}"
        
        # Build invoice payload for Xendit
        invoice_payload = {
            'external_id': external_id,
            'amount': amount,
            'description': f'DENR {service_type} Payment',
            'success_redirect_url': data.get('success_url', 'http://localhost:5000/user/history#services'),
            'failure_redirect_url': data.get('failure_url', 'http://localhost:5000/user/history#services'),
            'items': [
                {
                    'name': service_type,
                    'quantity': 1,
                    'price': amount
                }
            ]
        }

        if user_email:
            invoice_payload['payer_email'] = user_email
        
        # Add customer info if provided
        customer = {}
        if data.get('firstName'):
            customer['given_names'] = data.get('firstName')
        if data.get('lastName'):
            customer['surname'] = data.get('lastName')
        if user_email:
            customer['email'] = user_email
        if data.get('phone'):
            customer['mobile_number'] = data.get('phone')
        
        if customer:
            invoice_payload['customer'] = customer
        
        # Create invoice via Xendit API
        headers = {
            'Authorization': auth_header,
            'Content-Type': 'application/json'
        }
        
        response = requests.post(
            f'{XENDIT_BASE_URL}/v2/invoices',
            json=invoice_payload,
            headers=headers,
            timeout=10
        )
        
        if response.status_code in [200, 201]:
            invoice = response.json()
            
            # Save transaction record
            transaction_storage.add_transaction(
                user_email=user_email,
                external_id=external_id,
                invoice_id=invoice.get('id'),
                amount=amount,
                item_name=service_type,
                description=f'Service: {service_type}',
                status='Pending'
            )
            
            return jsonify({
                'status': 'success',
                'message': 'Payment initiated successfully',
                'invoice_id': invoice.get('id'),
                'paymentUrl': invoice.get('invoice_url'),
                'invoiceUrl': invoice.get('invoice_url'),
                'amount': invoice.get('amount'),
                'external_id': invoice.get('external_id')
            }), 201
        else:
            try:
                error_body = response.json()
            except ValueError:
                error_body = {'raw': response.text}
            return jsonify({
                'status': 'error',
                'message': f"Failed to create invoice: {response.status_code}",
                'details': error_body
            }), response.status_code
        
    except requests.exceptions.RequestException as e:
        return jsonify({
            'status': 'error',
            'message': f'Request failed: {str(e)}'
        }), 400
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500



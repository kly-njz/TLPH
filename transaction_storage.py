import firebase_admin
from firebase_admin import credentials

# Use your existing credentials file path
cred = credentials.Certificate("firebase-credentials.json")
firebase_admin.initialize_app(cred)

def add_finance_record(department, general_fund, special_fund, total_deposit, total_expenses, net_movement, collection_rate, recent_activity):
    """Add a finance record to Firestore under the specified department."""
    db = firestore.client()
    doc_id = f"{department}_{datetime.now().isoformat()}"
    record = {
        'general_fund': general_fund,
        'special_fund': special_fund,
        'total_deposit': total_deposit,
        'total_expenses': total_expenses,
        'net_movement': net_movement,
        'collection_rate': collection_rate,
        'recent_activity': recent_activity,
        'timestamp': firestore.SERVER_TIMESTAMP
    }
    db.collection('finance').document(doc_id).set({department: record})
    return doc_id

def add_revenue_mix_record(user_id, transaction_id, amount, details):
    """Add a revenue mix record for a transaction across users."""
    db = firestore.client()
    doc_id = f"{user_id}_{transaction_id}_{datetime.now().isoformat()}"
    record = {
        'user_id': user_id,
        'transaction_id': transaction_id,
        'amount': amount,
        'details': details,
        'timestamp': firestore.SERVER_TIMESTAMP
    }
    db.collection('revenue_mix').document(doc_id).set(record)
    return doc_id
def add_holiday_to_firestore(date_iso, name, description, holiday_type, office_status='closed', open_time='', close_time=''):
    """Add a holiday record to Firestore"""
    db = firestore.client()
    doc_id = f"{date_iso}|{name}"
    holiday = {
        'date': date_iso,
        'name': name,
        'description': description,
        'type': holiday_type,
        'office_status': office_status,
        'open_time': open_time,
        'close_time': close_time
    }
    db.collection('holidays').document(doc_id).set(holiday)
    return doc_id
from datetime import datetime
from firebase_admin import firestore

def get_db():
    """Get Firestore database reference"""
    return firestore.client()

def get_transactions_collection():
    """Get transactions collection reference"""
    return get_db().collection('transactions')

def add_transaction(user_email, external_id, invoice_id, amount, item_name, description, status='Pending', user_id=None):
    """Add a new transaction record to Firestore"""
    try:
        transactions_ref = get_transactions_collection()
        normalized_email = (user_email or 'guest@denr.gov.ph').strip().lower()
        
        transaction = {
            'user_email': normalized_email,
            'userId': user_id,
            'external_id': external_id,
            'invoice_id': invoice_id,
            'transaction_name': item_name,
            'description': description,
            'amount': amount,
            'status': status,
            'payment_method': 'Online Payment',
            'reference': external_id,
            'created_at': firestore.SERVER_TIMESTAMP,
            'updated_at': firestore.SERVER_TIMESTAMP,
            'paid_at': None
        }
        
        # Add document to Firestore
        doc_ref = transactions_ref.add(transaction)
        doc_id = doc_ref[1].id
        
        # Get the created document with server timestamp
        created_doc = transactions_ref.document(doc_id).get()
        result = created_doc.to_dict()
        result['id'] = doc_id

        # Record to financial_logs if payment is required
        if status and status.lower() in ['pending', 'unpaid', 'for payment']:
            try:
                record_transaction_to_financial_logs(transaction)
            except Exception as e:
                print(f"[WARN] Could not record to financial_logs: {e}")

        return result
    except Exception as e:
        print(f"Error adding transaction: {e}")
        return None

def update_transaction_status(invoice_id, status, payment_method=None, paid_at=None):
    """Update transaction status when webhook is received"""
    try:
        transactions_ref = get_transactions_collection()
        
        # Query for the transaction with this invoice_id
        query = transactions_ref.where('invoice_id', '==', invoice_id).limit(1)
        docs = query.stream()
        
        for doc in docs:
            update_data = {
                'status': status,
                'updated_at': firestore.SERVER_TIMESTAMP
            }
            
            if payment_method:
                update_data['payment_method'] = payment_method
            if paid_at:
                update_data['paid_at'] = paid_at
            elif status == 'PAID':
                update_data['paid_at'] = firestore.SERVER_TIMESTAMP
            
            # Update the document
            transactions_ref.document(doc.id).update(update_data)
            
            # Return updated document
            updated_doc = transactions_ref.document(doc.id).get()
            result = updated_doc.to_dict()
            result['id'] = doc.id
            return result
        
        return None
    except Exception as e:
        print(f"Error updating transaction: {e}")
        return None

def get_user_transactions(user_email=None, user_id=None):
    """Get all transactions for a specific user from Firestore"""
    try:
        transactions_ref = get_transactions_collection()
        
        transactions_by_id = {}
        
        # Strategy: Query by email first, then filter by userId logic
        # This handles both old records (no userId) and new records (with userId)
        if user_email:
            normalized_email = user_email.strip().lower()
            queries = [
                transactions_ref.where(filter=firestore.FieldFilter('user_email', '==', normalized_email))
            ]
            if user_email != normalized_email:
                queries.append(transactions_ref.where(filter=firestore.FieldFilter('user_email', '==', user_email)))
            
            for query in queries:
                for doc in query.stream():
                    transaction = doc.to_dict()
                    
                    # When userId is available, ONLY show transactions belonging to
                    # the current user. Excludes old records from deleted accounts
                    # that shared the same email.
                    if user_id:
                        if transaction.get('userId') != user_id:
                            continue
                    
                    transaction['id'] = doc.id
                    # Convert Firestore timestamps to ISO format strings
                    if 'created_at' in transaction and transaction['created_at']:
                        transaction['created_at'] = transaction['created_at'].isoformat() if hasattr(transaction['created_at'], 'isoformat') else str(transaction['created_at'])
                    if 'updated_at' in transaction and transaction['updated_at']:
                        transaction['updated_at'] = transaction['updated_at'].isoformat() if hasattr(transaction['updated_at'], 'isoformat') else str(transaction['updated_at'])
                    if 'paid_at' in transaction and transaction['paid_at']:
                        transaction['paid_at'] = transaction['paid_at'].isoformat() if hasattr(transaction['paid_at'], 'isoformat') else str(transaction['paid_at'])
                    transactions_by_id[doc.id] = transaction

        transactions = list(transactions_by_id.values())
        transactions.sort(key=lambda t: t.get('created_at') or '', reverse=True)
        return transactions
    except Exception as e:
        print(f"Error getting user transactions: {e}")
        return []

def get_all_transactions():
    """Get all transactions from Firestore"""
    try:
        transactions_ref = get_transactions_collection()
        query = transactions_ref.order_by('created_at', direction=firestore.Query.DESCENDING)
        
        transactions = []
        for doc in query.stream():
            transaction = doc.to_dict()
            transaction['id'] = doc.id
            # Convert timestamps
            if 'created_at' in transaction and transaction['created_at']:
                transaction['created_at'] = transaction['created_at'].isoformat() if hasattr(transaction['created_at'], 'isoformat') else str(transaction['created_at'])
            if 'updated_at' in transaction and transaction['updated_at']:
                transaction['updated_at'] = transaction['updated_at'].isoformat() if hasattr(transaction['updated_at'], 'isoformat') else str(transaction['updated_at'])
            transactions.append(transaction)
        
        return transactions
    except Exception as e:
        print(f"Error getting all transactions: {e}")
        return []

def find_transaction_by_external_id(external_id):
    """Find a transaction by external_id from Firestore"""
    try:
        transactions_ref = get_transactions_collection()
        query = transactions_ref.where('external_id', '==', external_id).limit(1)
        
        for doc in query.stream():
            transaction = doc.to_dict()
            transaction['id'] = doc.id
            return transaction
        
        return None
    except Exception as e:
        print(f"Error finding transaction: {e}")
        return None

def cancel_transaction_by_reference(reference, user_email=None, user_id=None):
    """Cancel a transaction by reference number (only if pending)"""
    try:
        transactions_ref = get_transactions_collection()
        
        # Query for transaction by reference or external_id
        query = transactions_ref.where('reference', '==', reference).limit(1)
        docs = list(query.stream())
        
        if not docs:
            query = transactions_ref.where('external_id', '==', reference).limit(1)
            docs = list(query.stream())
        
        if not docs:
            return {'success': False, 'message': 'Transaction not found'}
        
        doc = docs[0]
        transaction = doc.to_dict()
        
        # Verify it's the user's transaction (check userId first, then email)
        if user_id and transaction.get('userId') != user_id:
            return {'success': False, 'message': 'Unauthorized to cancel this transaction'}
        elif not user_id and transaction.get('user_email') != user_email:
            return {'success': False, 'message': 'Unauthorized to cancel this transaction'}
        
        # Only allow canceling pending transactions
        if transaction.get('status') != 'Pending':
            return {'success': False, 'message': f'Cannot cancel {transaction.get("status")} transaction'}
        
        # Cancel the transaction
        transactions_ref.document(doc.id).update({
            'status': 'Cancelled',
            'updated_at': firestore.SERVER_TIMESTAMP
        })
        
        # Get updated document
        updated_doc = transactions_ref.document(doc.id).get()
        result = updated_doc.to_dict()
        result['id'] = doc.id
        
        return {'success': True, 'transaction': result}
    except Exception as e:
        print(f"Error canceling transaction: {e}")
        return {'success': False, 'message': str(e)}

def record_transaction_to_financial_logs(transaction):
    """Record a user transaction that requires payment to the financial_logs collection."""
    from firebase_admin import firestore
    db = firestore.client()
    log = {
        'user_email': transaction.get('user_email'),
        'userId': transaction.get('userId'),
        'external_id': transaction.get('external_id'),
        'invoice_id': transaction.get('invoice_id'),
        'transaction_name': transaction.get('transaction_name'),
        'description': transaction.get('description'),
        'amount': transaction.get('amount'),
        'status': transaction.get('status'),
        'payment_method': transaction.get('payment_method', 'Online Payment'),
        'reference': transaction.get('reference'),
        'created_at': firestore.SERVER_TIMESTAMP,
        'updated_at': firestore.SERVER_TIMESTAMP,
        'paid_at': transaction.get('paid_at'),
        'source': 'transactions',
    }
    db.collection('financial_logs').add(log)

def record_all_user_financial_transactions():
    """Scan all user-related collections for financial transactions and record them to financial_logs."""
    from firebase_admin import firestore
    db = firestore.client()
    collections = [
        ('transactions', 'transaction_name'),
        ('applications', 'applicationType'),
        ('license_applications', 'licenseType'),
        ('service_requests', 'serviceType'),
        ('inventory_registrations', 'inventoryType'),
    ]
    for col, type_field in collections:
        try:
            docs = db.collection(col).stream()
            for doc in docs:
                data = doc.to_dict()
                # Only record if there is an amount/fee/payment required
                amount = data.get('amount') or data.get('fee') or data.get('investmentQty')
                if amount and float(amount) > 0:
                    log = {
                        'user_email': data.get('user_email') or data.get('email'),
                        'userId': data.get('userId'),
                        'external_id': data.get('external_id') or data.get('externalId'),
                        'invoice_id': data.get('invoice_id'),
                        'transaction_name': data.get(type_field) or data.get('transaction_name'),
                        'description': data.get('description'),
                        'amount': amount,
                        'status': data.get('status'),
                        'payment_method': data.get('payment_method', 'Online Payment'),
                        'reference': data.get('reference') or data.get('external_id'),
                        'created_at': data.get('created_at'),
                        'updated_at': data.get('updated_at'),
                        'paid_at': data.get('paid_at'),
                        'source': col,
                    }
                    db.collection('financial_logs').add(log)
        except Exception as e:
            print(f"[ERROR] Scanning {col}: {e}")

# At the bottom of the file, add a CLI entry point for manual backfill
if __name__ == "__main__":
    print("Backfilling all user financial transactions to financial_logs...")
    record_all_user_financial_transactions()
    print("Done. Check your Firestore financial_logs collection.")

# 🔌 DENR TLPH - Payment Routes & API Reference

## 📋 Main Routes File
**Location:** `routes/main_routes.py`

### Public Payment Routes (No Auth Required)

#### 1. Payment Success Page
```
GET /payment-success
├─ Template: templates/payment-success.html
├─ Auth: None (Public)
└─ Purpose: Display after successful Xendit payment
```

#### 2. Payment Failed Page
```
GET /payment-failed
├─ Template: templates/payment-failed.html
├─ Auth: None (Public)
└─ Purpose: Display after failed Xendit payment
```

---

## 💳 Payments Routes File
**Location:** `routes/payments_routes.py` (641 lines)

### Payment Gateway Endpoints

#### 1. Create Xendit Invoice
```
POST /api/payments/create-invoice

Request Payload:
{
  "email": "user@example.com",
  "first_name": "Juan",
  "last_name": "Dela Cruz",
  "phone": "+63912345678",
  "amount": 5000,
  "item_name": "Environmental Clearance",
  "description": "License application fee",
  "service_type": "environmental_clearance",
  "success_url": "http://localhost:5000/payment-success",
  "failure_url": "http://localhost:5000/payment-failed"
}

Response (Success):
{
  "status": "success",
  "invoice_id": "inv-xxxxx",
  "external_id": "svc-abc123",
  "payment_url": "https://checkout.xendit.co/?id=inv-xxxxx",
  "amount": 5000
}

Response (Error):
{
  "status": "error",
  "message": "Amount must be greater than 0"
}
```

#### 2. Record Transaction
```
POST /api/payments/record-transaction

Request Payload:
{
  "invoice_id": "inv-xxxxx",
  "external_id": "svc-abc123",
  "payer_email": "user@example.com",
  "amount": 5000,
  "description": "Environmental Clearance",
  "payment_method": "credit_card",
  "status": "paid",
  "paid_at": "2026-03-06T10:30:00Z",
  "reference": "REF-12345"
}

Response:
{
  "success": true,
  "transaction_id": "tx-doc-id",
  "message": "Transaction recorded"
}
```

#### 3. Get Invoice Status
```
GET /api/payments/invoice-status/<external_id>

Response:
{
  "status": "completed",
  "invoice_id": "inv-xxxxx",
  "external_id": "svc-abc123",
  "amount": 5000,
  "paid_at": "2026-03-06T10:30:00Z",
  "payment_method": "credit_card"
}
```

#### 4. Generate Payment Receipt (PDF)
```
GET /api/payments/receipt/<invoice_id>

Response: PDF File (BytesIO)
├─ Invoice Details
├─ Payer Information
├─ Amount
├─ Payment Date
└─ Receipt Number
```

---

## 🏢 Municipal API Routes
**Location:** `routes/municipal_api_logs.py`

### Municipal Deposits Endpoint

#### Get Municipal Payment Deposits
```
GET /api/municipal/deposits/payments

Auth: @role_required('municipal','municipal_admin')
Session Requirement: municipality

Query Parameters:
├─ filter (optional): "all" | "paid" | "pending"
├─ limit (optional): number (default: 1000)
└─ offset (optional): number (default: 0)

Response:
{
  "success": true,
  "municipality": "Quezon City",
  "region": "REGION-III",
  "total_amount": 125000.00,
  "total_payments": 25,
  "deposits": [
    {
      "id": "tx-doc-id",
      "transaction_type": "Payment Deposit",
      "payment_type": "Online Payment",
      "invoice_id": "INV-12345",
      "external_id": "svc-abc123",
      "amount": 5000,
      "description": "Environmental Clearance",
      "payer_email": "user@example.com",
      "payment_method": "Credit Card",
      "status": "PAID",
      "created_at": "2026-03-06T09:15:00Z",
      "paid_at": "2026-03-06T10:30:00Z",
      "reference": "REF-12345",
      "source": "transactions",
      "municipality": "Quezon City",
      "region": "REGION-III"
    },
    ...
  ]
}
```

**Backend Logic:**
```python
@bp.route('/deposits/payments', methods=['GET'])
def api_get_municipal_payment_deposits():
    # 1. Authenticate municipal_admin role
    # 2. Get municipality from session
    # 3. Query users collection for municipality members
    # 4. Query transactions collection
    # 5. Filter by:
    #    - Payer email in municipality users
    #    - OR municipality field matches
    #    - AND status in {paid, completed, settled, approved, success}
    #    - AND amount > 0
    # 6. Normalize response with consistent schema
    # 7. Return sorted by created_at DESC
```

---

## 🌍 Regional API Routes
**Location:** `routes/regional_routes.py`

### Regional Deposits Endpoints

#### Get Regional Payment Deposits
```
GET /regional/api/deposits/payments

Auth: @role_required('regional','regional_admin')
Session Requirement: region

Query Parameters:
├─ municipality (optional): filter by specific municipality
├─ status (optional): "paid" | "pending" | "failed"
├─ limit (optional): number
└─ offset (optional): number

Response:
{
  "success": true,
  "region": "REGION-III",
  "scoped_municipalities": ["Quezon City", "Marikina", "Pasig"],
  "total_amount": 500000.00,
  "total_payments": 100,
  "unique_payers": 87,
  "payment_deposits": [
    {
      "id": "tx-doc-id",
      "invoice_id": "INV-12345",
      "description": "Permit Application",
      "amount": 5000,
      "status": "PAID",
      "payment_method": "Online Payment",
      "municipality": "Quezon City",
      "payer_email": "user@example.com",
      "created_at": "2026-03-06T09:15:00Z",
      "source": "transactions"
    },
    ...
  ]
}
```

**Backend Logic:**
```python
# 1. Authenticate regional_admin role
# 2. Get region from session
# 3. Get municipalities list for region
# 4. Query users collection for region members
# 5. Query transactions collection
# 6. Filter by:
#    - Payer email in region users
#    - OR municipality in region municipalities
#    - AND region matches
#    - AND status is PAID
#    - AND amount > 0
# 7. Apply municipality filter if provided
# 8. Return with region-wide aggregations
```

---

## 🏛️ National/Super Admin Routes
**Location:** `routes/national_routes.py`

### National Dashboard (Under Construction)
```
GET /national/accounting/payments

Auth: @role_required('national','national_admin')

Purpose:
├─ View ALL payments across ALL regions
├─ Aggregate statistics by region
├─ Filter by any region/municipality
└─ Export all data
```

---

## 📊 Frontend Endpoints (HTML Pages by User Role)

### User (Citizen/Applicant)
```
User Service Application
    ↓
POST /api/payments/create-invoice (Frontend)
    ↓
Xendit Checkout Opens
    ↓
Payment Completion
    ↓
POST /api/payments/record-transaction
    ↓
GET /payment-success or /payment-failed
```

### Municipal Admin
```
GET /accounting/payment-deposits
    ↓
Alpine.js Component: paymentDeposits()
    ↓
GET /api/municipal/deposits/payments (Backend)
    ↓
Displays in Table + Charts
    ├─ Filter by status
    ├─ Search by payer
    ├─ View trends
    └─ Export CSV
```

### Regional Admin
```
GET /accounting/deposit-category
    ↓
HTML Page with Filters
    ↓
GET /regional/api/deposits/payments (Backend)
    ↓
Displays in Table + Charts
    ├─ Filter by municipality
    ├─ Filter by status
    ├─ Search by payer
    ├─ View trends
    ├─ Manage categories (Modal)
    └─ Export CSV
```

### National Admin
```
GET /national/accounting/payments
    ↓
GET /api/national/deposits/payments (Backend - TODO)
    ↓
Displays ALL regions/municipalities
    ├─ Aggregate view by region
    ├─ Filter by any region
    ├─ Filter by any municipality
    ├─ View trends
    └─ Export all data
```

---

## 🔑 Authentication & Authorization

### Role-Based Access Control (RBAC)

```python
@role_required decorator checks:
├─ Session for user_id + email
├─ Firebase auth token validity
├─ User document in Firestore
├─ User role field
└─ Allowed roles list

Municipal Admin:
├─ Accesses /api/municipal/deposits/payments
├─ Sees only municipality data
└─ Gets municipality from session

Regional Admin:
├─ Accesses /regional/api/deposits/payments
├─ Sees region data
└─ Gets region from session

National Admin:
├─ Accesses /api/national/deposits/payments (TODO)
├─ Sees all data
└─ No regional/municipality scope
```

---

## 📤 Data Flow: Transaction → Database → UI

### Step 1: User Initiates Payment
```
/payment-form/<service_type>
│
├─ Service: environmental_clearance | permit | license | other
├─ Amount: Varies by service
├─ Payer: User account info
└─ Description: Service details
```

### Step 2: Create Xendit Invoice
```
POST /api/payments/create-invoice
│
├─ Xendit API receives request
├─ Validates amount > 0
├─ Generates invoice_id + external_id
├─ Creates checkout form
└─ Returns payment_url
```

### Step 3: User Pays via Xendit
```
Xendit Checkout Page
│
├─ Payment Methods:
│  ├─ Credit/Debit Card
│  ├─ Bank Transfer
│  └─ E-wallets
├─ User enters card/account details
├─ Xendit processes payment
└─ Redirect to success/failed URL
```

### Step 4: Record Transaction
```
POST /api/payments/record-transaction
│
├─ Firestore transactions collection
├─ Document created with:
│  ├─ invoice_id
│  ├─ external_id (Xendit ref)
│  ├─ user info
│  ├─ amount + status
│  ├─ payment_method
│  ├─ created_at + paid_at
│  ├─ municipality + region
│  └─ source = "transactions"
└─ Transaction stored permanently
```

### Step 5: Admin Views Transaction
```
Municipal Admin:
├─ GET /api/municipal/deposits/payments
├─ Firestore query filters by municipality
└─ Display in payment-deposits-municipal.html

Regional Admin:
├─ GET /regional/api/deposits/payments
├─ Firestore query filters by region + municipality
└─ Display in deposit-category-regional.html

National Admin:
├─ GET /api/national/deposits/payments (TODO)
├─ Firestore query fetches all
└─ Display in national accounting dashboard
```

---

## 🔄 Request/Response Examples

### Create Invoice Request
```bash
curl -X POST http://localhost:5000/api/payments/create-invoice \
  -H "Content-Type: application/json" \
  -d '{
    "email": "juan@example.com",
    "first_name": "Juan",
    "last_name": "Dela Cruz",
    "phone": "+63912345678",
    "amount": 5000,
    "item_name": "Permit Fee",
    "description": "Fish Pen Permit",
    "service_type": "fisheries",
    "success_url": "http://localhost:5000/payment-success",
    "failure_url": "http://localhost:5000/payment-failed"
  }'
```

### Record Transaction Request
```bash
curl -X POST http://localhost:5000/api/payments/record-transaction \
  -H "Content-Type: application/json" \
  -d '{
    "invoice_id": "inv-123456",
    "external_id": "svc-abc123def456",
    "payer_email": "juan@example.com",
    "amount": 5000,
    "description": "Fish Pen Permit",
    "payment_method": "credit_card",
    "status": "paid",
    "paid_at": "2026-03-06T10:30:00Z",
    "reference": "REF-20260306-001"
  }'
```

### Get Municipal Deposits
```bash
curl -X GET "http://localhost:5000/api/municipal/deposits/payments?filter=paid&limit=50" \
  -H "Authorization: Bearer <firebase-token>"
```

---

## ❌ Error Handling

### Common Errors

#### Invalid Amount
```json
{
  "status": "error",
  "message": "Amount must be greater than 0"
}
```

#### Invalid Email
```json
{
  "status": "error",
  "message": "Invalid payer email"
}
```

#### Authentication Failed
```json
{
  "success": false,
  "error": "Cannot determine municipality"
}
```

#### Not Authorized
```json
{
  "status": "error",
  "message": "Not authorized to access this resource"
}
```

---

## 🔐 Security Measures

1. **Authentication:** Firebase auth tokens required for admin endpoints
2. **Authorization:** @role_required decorators enforce role-based access
3. **Scope Limiting:** Municipal admins see only their municipality
4. **Data Validation:** Amount > 0, valid email format, required fields
5. **PII Protection:** Email addresses hashed in logs
6. **Audit Trail:** All transactions timestamped and immutable in Firestore
7. **Payment Security:** Xendit handles card data (PCI compliant)
8. **HTTPS:** All payment endpoints use HTTPS in production

---

## 📈 Performance Considerations

- **Pagination:** Limit returned records (default: 1000)
- **Caching:** Frontend uses Alpine.js component caching
- **Indexing:** Firestore queries on municipality + status fields
- **Aggregation:** Pre-calculate totals on frontend (not DB-heavy)
- **Lazy Loading:** Charts render only when visible in viewport

---

## 🚀 Future Enhancements

1. [ ] Add National Admin aggregated view
2. [ ] Implement real-time webhook updates from Xendit
3. [ ] Add payment reconciliation logic
4. [ ] Create reports by category/type
5. [ ] Implement payment refunds tracking
6. [ ] Add late fee calculation
7. [ ] Create audit log export
8. [ ] Add 2FA for high-value payments


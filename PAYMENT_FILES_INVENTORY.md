# 📂 Payment System - Complete File Inventory

## 📍 Frontend Files (HTML/Templates)

### User Level (Public/Authenticated Users)
| File | Path | Lines | Purpose |
|------|------|-------|---------|
| payment-form.html | `templates/` | 237 | Main payment form for all services (Xendit integration) |
| payment-success.html | `templates/` | ~50 | Success confirmation page |
| payment-failed.html | `templates/` | ~50 | Failure notification page |
| transaction.html | `templates/user/` | ~500 | User transaction initiation page |
| transaction-history.html | `templates/user/` | ~600 | User payment history view |

**What They Do:**
- `payment-form.html` - Collects payer info (name, email, phone, amount, description) and submits to Xendit
- `payment-success.html` - Shows success banner with receipt details
- `payment-failed.html` - Shows error message with retry option
- `transaction.html` - Lists available services, rates, shows payment button
- `transaction-history.html` - Shows user's past transactions with status

### Municipal Admin Level
| File | Path | Lines | Goal |
|------|------|-------|------|
| payment-deposits-municipal.html | `templates/municipal/accounting/` | 362 | View all payments from municipality |

**What It Does:**
- Alpine.js component: `paymentDeposits()` 
- Shows 4 stat cards: Total Deposits, Payment Count, Completed, Pending
- Renders 2 charts: Payment Status Distribution (doughnut), Deposits by Type (bar)
- Interactive table with filters: Search, Status filter, Municipality scope
- Fetches from: `GET /api/municipal/deposits/payments`
- Role protection: `@role_required('municipal','municipal_admin')`

### Regional Admin Level
| File | Path | Lines | Goal |
|------|------|-------|------|
| deposit-category-regional.html | `templates/regional/accounting/` | 464 | View region payments + manage categories |

**What It Does:**
- Non-Alpine.js page (jQuery-style filtering)
- Shows 3 stat cards: Total Paid Amount, Paid Transactions, Unique Payers
- Renders 2 charts: Deposit Trends (line), Payment Status Mix (doughnut)
- Interactive table with filters: Municipality dropdown, Search, Status filter
- Modal for adding deposit categories (Demo only)
- Fetches from: `GET /regional/api/deposits/payments` (TODO - needs backend)
- Role protection: `@role_required('regional','regional_admin')`

### Super Admin Level
| File | Path | Lines | Goal |
|------|------|-------|------|
| (NOT YET CREATED) | `templates/super-admin/accounting/` | TBD | Aggregate view of all regions |

**Needed:**
- National-level payment dashboard
- Aggregate stats by region
- Filter by any region/municipality
- Export all data

---

## ⚙️ Backend Files (Python/Routes)

### Main Routes
**File:** `routes/main_routes.py`

| Route | Method | Auth | Purpose |
|-------|--------|------|---------|
| `/payment-success` | GET | None | Render payment-success.html |
| `/payment-failed` | GET | None | Render payment-failed.html |

```python
@bp.route('/payment-success')
def payment_success():
    return render_template('payment-success.html')

@bp.route('/payment-failed')
def payment_failed():
    return render_template('payment-failed.html')
```

### Payments Routes
**File:** `routes/payments_routes.py` (641 lines)

| Route | Method | Auth | Purpose | Response |
|-------|--------|------|---------|----------|
| `/api/payments/create-invoice` | POST | None | Create Xendit invoice | `{status, invoice_id, external_id, payment_url}` |
| `/api/payments/record-transaction` | POST | None | Store transaction in DB | `{success, transaction_id}` |
| `/api/payments/invoice-status/<id>` | GET | None | Check payment status | `{status, amount, paid_at}` |
| `/api/payments/receipt/<id>` | GET | Optional | Download PDF receipt | PDF File |

**Key Code:**
```python
def create_invoice():
    # 1. Validate request (amount, email)
    # 2. Generate unique external_id
    # 3. Call Xendit API to create invoice
    # 4. Return payment_url

def record_transaction():
    # 1. Validate invoice exists (Xendit check)
    # 2. Store in transactions collection
    # 3. Update transaction status
    # 4. Return success

def get_invoice_status():
    # 1. Query Xendit for invoice status
    # 2. Return payment state
    # 3. Update local DB if needed
```

### Municipal API Routes  
**File:** `routes/municipal_api_logs.py` (1523 lines)

| Route | Method | Auth | Purpose | Response |
|-------|--------|------|---------|----------|
| `/api/municipal/deposits/payments` | GET | `@role_required('municipal','municipal_admin')` | Get municipality payments | `{municipality, region, total_amount, deposits[]}` |

**Key Code (Lines 379-480):**
```python
@bp.route('/deposits/payments', methods=['GET'])
def api_get_municipal_payment_deposits():
    # 1. Authenticate + get municipality from session
    # 2. Fetch all users in municipality
    # 3. Query transactions collection filtered by:
    #    - payer_email in municipality_users OR municipality field matches
    #    - status in {paid, completed, settled, approved, success}
    #    - amount > 0
    # 4. Normalize response with consistent schema
    # 5. Sort by created_at DESC
    # 6. Return JSON
```

**Firestore Query Used:**
```python
db.collection('transactions')
  .where('status', 'in', ['paid', 'completed', 'settled', 'approved', 'success'])
  .stream()
```

**Response Schema:**
```json
{
  "deposits": [
    {
      "id": "doc-id",
      "transaction_type": "Payment Deposit",
      "invoice_id": "INV-12345",
      "external_id": "svc-abc123",
      "amount": 5000.00,
      "description": "Environmental Clearance",
      "payer_email": "user@example.com",
      "payment_method": "Credit Card",
      "status": "PAID",
      "created_at": "2026-03-06T09:15:00Z",
      "paid_at": "2026-03-06T10:30:00Z",
      "municipality": "Quezon City",
      "region": "REGION-III"
    }
  ]
}
```

### Regional API Routes
**File:** `routes/regional_routes.py` (3432 lines)

| Route | Method | Auth | Purpose | Response |
|-------|--------|------|---------|----------|
| `/regional/api/deposits/payments` | GET | `@role_required('regional','regional_admin')` | Get region payments | `{region, scoped_municipalities, total_amount, payment_deposits[]}` |

**Key Code (Lines 2300-2450):**
```python
# 1. Authenticate + get region from session
# 2. Get municipalities list for region
# 3. Fetch all users in region
# 4. Query transactions collection filtered by:
#    - payer_email in region_users OR municipality in region OR region field matches
#    - status in {paid, completed, settled, approved, success}
#    - amount > 0
# 5. Optional municipality filter from query params
# 6. Normalize response
# 7. Return JSON
```

**Firestore Query Used:**
```python
db.collection('transactions')
  .where('region', '==', user_region)
  .stream()
```

**Response Schema (Enhanced):**
```json
{
  "region": "REGION-III",
  "scoped_municipalities": ["Quezon City", "Marikina", "Pasig"],
  "total_amount": 500000.00,
  "total_payments": 100,
  "unique_payers": 87,
  "payment_deposits": [
    {
      "id": "doc-id",
      "invoice_id": "INV-12345",
      "amount": 5000.00,
      "status": "PAID",
      "municipality": "Quezon City",
      "payer_email": "user@example.com",
      "created_at": "2026-03-06T09:15:00Z"
    }
  ]
}
```

### National Admin Routes
**File:** `routes/national_routes.py` (1428 lines)

**Status:** ❌ NEEDS IMPLEMENTATION

| Route | Method | Auth | Purpose | Response |
|-------|--------|------|---------|----------|
| `/accounting/payments` | GET | `@role_required('national','national_admin')` | (TODO) Render national dashboard | HTML |
| `/api/national/deposits/payments` | GET | `@role_required('national','national_admin')` | (TODO) Get all payments | `{all_deposits, by_region, statistics}` |

**TODO Implementation:**
```python
@bp.route('/accounting/payments')
@role_required('national','national_admin')
def accounting_payments():
    # Fetch aggregate payment data
    # Pass to template: templates/national/accounting/payments-national.html
    return render_template('...')

@bp.route('/api/national/deposits/payments', methods=['GET'])
@role_required('national','national_admin')
def api_get_national_payment_deposits():
    # No scope filtering
    # Query all transactions
    # Filter by requested region/municipality from query params
    # Return comprehensive data
```

---

## 🗄️ Database Collections

### Firestore Collection: `transactions`
**Location:** Firestore root

**Document Schema:**
```json
{
  "id": "doc-id",
  "invoiceId": "INV-12345",
  "externalId": "svc-abc123def456",
  "userId": "firebase-user-id",
  "userEmail": "user@example.com",
  "amount": 5000.00,
  "description": "Environmental Clearance Certificate",
  "status": "paid",
  "paymentStatus": "success",
  "paymentMethod": "credit_card",
  "payer_email": "user@example.com",
  "municipality": "Quezon City",
  "region": "REGION-III",
  "created_at": "2026-03-06T09:15:00Z",
  "paid_at": "2026-03-06T10:30:00Z",
  "reference": "REF-20260306-001",
  "source": "transactions",
  "payment_method": "ONLINE PAYMENT",
  "service_type": "environmental_clearance"
}
```

**Indexes Needed:**
```
- municipality + status
- region + status
- payer_email + status
- created_at DESC
- status (for PAID filtering)
```

### Firestore Collection: `users`
**Location:** Firestore root

**Document Schema (Relevant Fields):**
```json
{
  "email": "user@example.com",
  "municipality": "Quezon City",
  "region": "REGION-III",
  "uid": "firebase-uid",
  "user_id": "custom-user-id",
  "role": "user",
  "status": "active"
}
```

**Used For:** Filtering transactions by municipality/region

---

## 📊 Data Files (Documentation)

| File | Path | Purpose |
|------|------|---------|
| PAYMENT_SYSTEM_OVERVIEW.md | `root/` | High-level architecture + flow |
| PAYMENT_ROUTES_REFERENCE.md | `root/` | Detailed API endpoints + examples |
| This File | `root/` | Complete file inventory |

---

## 🔍 Quick File Location Guide

### "Where is the municipal payment view?"
- **Frontend:** `templates/municipal/accounting/payment-deposits-municipal.html`
- **Backend:** `routes/municipal_api_logs.py` lines 379-480
- **Endpoint:** `GET /api/municipal/deposits/payments`

### "Where is the regional payment view?"
- **Frontend:** `templates/regional/accounting/deposit-category-regional.html`
- **Backend:** `routes/regional_routes.py` lines 2300-2450
- **Endpoint:** `GET /regional/api/deposits/payments`

### "Where is the payment form?"
- **Frontend:** `templates/payment-form.html` (Shared for all users)
- **Backend:** `routes/payments_routes.py` lines 252-300 (GET), 503-550 (POST)
- **Endpoint:** `POST /api/payments/create-invoice`

### "Where is the payment success page?"
- **Frontend:** `templates/payment-success.html`
- **Backend:** `routes/main_routes.py` line 416
- **Route:** `GET /payment-success`

### "Where do transactions get stored?"
- **Firestore Collection:** `transactions`
- **Code:** `routes/payments_routes.py` - `record_transaction()` function
- **Endpoint:** `POST /api/payments/record-transaction`

### "How does municipal admin see their payments?"
1. User logs in as municipal_admin
2. Navigates to `/accounting/payment-deposits`
3. Page loads `payment-deposits-municipal.html`
4. Alpine.js component calls `GET /api/municipal/deposits/payments`
5. Backend checks role + municipality from session
6. Firestore query returns only that municipality's transactions
7. Frontend renders table + charts with real data

---

## ✅ Implementation Checklist

### Completed ✓
- [x] Payment form (Xendit integration)
- [x] Payment success/failed pages
- [x] Record transaction endpoint
- [x] Municipal deposits view (frontend + backend)
- [x] Regional deposits view (frontend)
- [x] User transaction pages
- [x] Firestore transactions collection
- [x] Authentication/Authorization middleware

### In Progress 🔄
- [ ] Regional deposits backend endpoint (exists but may need testing)
- [ ] Regional category management modal (frontend only)

### TODO ❌
- [ ] National admin payment dashboard (frontend + backend)
- [ ] Payment refunds tracking
- [ ] Category-based reporting
- [ ] Xendit webhook integration (real-time updates)
- [ ] Payment reconciliation page
- [ ] Detailed transaction view modal
- [ ] Batch payment processing
- [ ] Advanced filters (date range, amount range)

---

## 🔐 Security Summary

| Component | Method | Status |
|-----------|--------|--------|
| User Input Validation | Amount > 0, valid email format | ✅ Implemented |
| Role-Based Access | @role_required decorators | ✅ Implemented |
| Data Scoping | Municipal/Regional filtering | ✅ Implemented |
| PII Protection | Minimal logging of emails | ⚠️ Partial |
| Payment Processing | Xendit (PCI compliant) | ✅ Implemented |
| Audit Trail | Timestamps + immutable records | ✅ Implemented |
| HTTPS | Should be enforced | ⚠️ Dev mode warning |
| Token Expiry | Firebase handles | ✅ Implemented |

---

## 📈 Current Status Dashboard

```
Frontend Components:
├─ User Level: ✅ 5/5 files complete
├─ Municipal Level: ✅ 1/1 file complete
├─ Regional Level: ⚠️ 1/1 file complete (missing backend)
└─ National Level: ❌ 0/1 needed

Backend Endpoints:
├─ Payments: ✅ 4 endpoints working
├─ Municipal: ✅ 1 endpoint working
├─ Regional: ⚠️ 1 endpoint (needs testing)
└─ National: ❌ 0 endpoints (TODO)

Database:
├─ Collections: ✅ transactions + users
├─ Indexes: ⚠️ May need optimization
└─ Schema: ✅ Defined

Documentation:
├─ Overview: ✅ PAYMENT_SYSTEM_OVERVIEW.md
├─ API Ref: ✅ PAYMENT_ROUTES_REFERENCE.md
└─ Inventory: ✅ This file
```

---

## 🚀 Quick Start for Developers

1. **View User Payment Flow:**
   - Start at `templates/payment-form.html`
   - See `routes/payments_routes.py`

2. **Add Municipal Admin Payment View:**
   - Already done! Check `templates/municipal/accounting/payment-deposits-municipal.html`
   - Endpoint: `GET /api/municipal/deposits/payments`

3. **Add Regional Admin Payment View:**
   - Already done! Check `templates/regional/accounting/deposit-category-regional.html`
   - Endpoint needs verification: `GET /regional/api/deposits/payments`

4. **Add National Admin View:**
   - Create `templates/national/accounting/payments-national.html`
   - Add route to `routes/national_routes.py`
   - Add endpoint to get all transactions


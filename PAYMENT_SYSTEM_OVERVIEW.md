# 💰 DENR TLPH - Payment System Overview

## 📍 Payment Files Structure

### User Level (Citizens/License Applicants)
**Location:** `templates/user/`
- `transaction.html` - Main payment initiation page
- `transaction-history.html` - Completed transactions history
- Service form pages → Payment form page

**Payment Flow:**
1. User applies for license/permit (service form)
2. Redirected to `payment-form.html` (shared)
3. Xendit payment gateway handles transaction
4. Success → `payment-success.html` / Failure → `payment-failed.html`
5. Transaction stored in Firestore `transactions` collection

---

### Municipal Level (Municipality Admin)
**Location:** `templates/municipal/accounting/`

#### 1. **payment-deposits-municipal.html** (362 lines)
##### Code Structure:
```javascript
// Alpine.js Component: paymentDeposits()
x-data="paymentDeposits()" 
x-init="loadDeposits()"
```

##### Key Features:
- **Stats Cards (4):**
  - Total Deposits (₱)
  - Payment Count
  - Completed Payments
  - Pending Amount (₱)

- **Charts:**
  - Payment Status Distribution (Doughnut)
  - Deposits by Type (Bar/Line)

- **Data Table:**
  - Invoice ID
  - Payer Email
  - Description
  - Source (Online Payment/License Fee)
  - Amount (₱)
  - Status (PAID, PENDING, FAILED)
  - Municipality Badge
  - Created Date

- **Filters:**
  - Search by invoice/payer
  - Status filter (Paid, Pending, Failed)
  - Municipality scope
  - Reset filters button

##### Backend Endpoint:
```
GET /api/municipal/deposits/payments
@role_required('municipal','municipal_admin')
```

**Query Logic:**
1. Authenticates municipal admin
2. Gets municipality scope from session
3. Fetches ALL users in that municipality
4. Filters transactions where:
   - Payer email in municipality users
   - OR municipality field matches
5. Returns PAID transactions only (status in: {paid, completed, settled, approved, success})
6. Data source: Firestore `transactions` collection

---

### Regional Level (Region Admin)
**Location:** `templates/regional/accounting/`

#### 1. **deposit-category-regional.html** (464 lines)
##### Code Structure:
```html
x-data="{ modalOpen:false }"
```

##### Key Features:
- **Stats Cards (3):**
  - Total Paid Amount (₱)
  - Paid Transactions Count
  - Unique Payers Count

- **Charts:**
  - Deposit Trends (Line Chart)
  - Payment Status Mix (Doughnut)

- **Data Table:**
  - Invoice ID
  - Payer Email
  - Description (Permit, License, etc)
  - Source (transactions/license_payments)
  - Amount (₱)
  - Status (PAID, COMPLETED, SETTLED)
  - Municipality (Within Region)
  - Date

- **Filters:**
  - Municipality dropdown (dynamic per region)
  - Search by payer/invoice
  - Revenue/Status filter
  - Reset button
  - Export CSV button

- **Modal:**
  - Add Deposit Category form
  - Fields: Category Name, COA Account, Revenue Type, Tax Type, Tax Rate, Budget Code, Region (Read-only), Municipality Scope
  - Save/Cancel buttons

##### Backend Endpoint:
```
GET /api/regional/deposits/payments
@role_required('regional','regional_admin')
```

**Query Logic:**
1. Authenticates regional admin
2. Gets region scope from session
3. Fetches ALL users in that region
4. Gets municipalities list for region
5. Filters transactions where:
   - Payer email in region users
   - OR municipality in region municipalities
   - AND region matches
6. Returns PAID transactions only
7. Data source: Firestore `transactions` collection

---

## 💳 Payment Processing Flow

### 1. **User Payment Initiation**
```
User Service Form → /payment-form/<service_type>
↓
payment-form.html (shared)
↓
Collects: Name, Email, Phone, Amount, Item, Description
```

### 2. **Payment Route Handler**
```
POST /api/payments/create-invoice
↓
Creates Xendit Invoice with:
  - external_id (svc-{uuid})
  - amount (PHP)
  - description
  - customer info
  - redirect URLs
↓
Returns: Invoice ID, Payment URL
```

### 3. **Xendit Gateway**
```
Xendit Checkout (v2) handles:
  - Credit/Debit Card
  - Bank Transfer
  - E-wallets (configured)
```

### 4. **Transaction Recording**
```
POST /api/payments/record-transaction
↓
Stores in Firestore: transactions collection
{
  invoiceId: string
  externalId: string (Xendit)
  userId: string
  userEmail: string
  amount: number
  description: string
  status: "paid" | "pending" | "failed"
  paymentMethod: string
  paymentStatus: string
  payer_email: string
  created_at: timestamp
  paid_at: timestamp
  source: "transactions" | "license_payments"
  municipality: string
  region: string
}
```

### 5. **Success Redirect**
```
/payment-success → payment-success.html
↓
Displays confirmation
Stores receipt in Firestore
```

### 6. **Admin Views**
```
Municipal: /accounting/payment-deposits
↓ (scoped to municipality)
Shows all PAID transactions from municipality users

Regional: /accounting/deposit-category
↓ (scoped to region)
Shows all PAID transactions from region municipalities
```

---

## 📊 Data Flow Diagram

```
┌─────────────────┐
│ User Payment    │
│ (transaction)   │
└────────┬────────┘
         │
    ┌────▼─────────────────────┐
    │  Firestore                │
    │  transactions collection  │
    └────┬─────────────────────┘
         │
    ┌────┴─────────────────────────────────┐
    │                                       │
┌───▼──────────────────┐      ┌────────────▼──┐
│ Municipal Admin View  │      │ Regional Admin │
│ /api/municipal/      │      │ /api/regional/ │
│ deposits/payments    │      │ deposits/      │
│ (Scoped to Muni)     │      │ payments       │
└───────────────────────┘      └────────────────┘
```

---

## 🔐 Authentication & Scoping

### Municipal Deposits Endpoint
```python
@role_required('municipal','municipal_admin')
municipalities_scope = session.get('municipality')
# Only sees transactions from their municipality
```

### Regional Deposits Endpoint
```python
@role_required('regional','regional_admin')
region_scope = session.get('region')
# Only sees transactions from their region
# Can filter by municipality within region
```

### National Deposits Endpoint
```python
@role_required('national','national_admin')
# Sees ALL transactions across all regions/municipalities
# Can filter by any region or municipality
```

---

## 📋 Firestore Collections Used

### `transactions` Collection
```
{
  "invoiceId": "INV-xxx",
  "externalId": "svc-xxx",
  "userId": "user-doc-id",
  "userEmail": "user@example.com",
  "amount": 5000,
  "description": "Environmental Clearance Certificate",
  "status": "paid",
  "paymentMethod": "credit_card",
  "paymentStatus": "success",
  "municipality": "Quezon City",
  "region": "REGION-III",
  "created_at": "2026-03-06T...",
  "paid_at": "2026-03-06T...",
  "source": "transactions",
  "payer_email": "applicant@email.com",
  "reference": "REF-123",
  "payment_method": "ONLINE PAYMENT"
}
```

### `users` Collection (reference for filtering)
```
{
  "email": "user@example.com",
  "municipality": "Quezon City",
  "region": "REGION-III",
  "uid": "firebase-uid",
  "user_id": "custom-id"
}
```

---

## 🔄 Available Operations

### Municipal Admin Can:
- ✅ View all payments from their municipality
- ✅ Filter by payment status
- ✅ Search by payer/invoice
- ✅ Export CSV of payments
- ✅ View payment trends/charts
- ✅ See payment methods used

### Regional Admin Can:
- ✅ View all payments from their region
- ✅ Filter by municipality (dropdown)
- ✅ Filter by payment status
- ✅ Search by payer/invoice
- ✅ Export CSV of payments
- ✅ View regional payment trends
- ✅ See deposit category management modal
- ✅ Create deposit categories (per municipality scope)

### National Admin Can:
- ✅ View ALL payments across all regions
- ✅ Filter by any region
- ✅ Filter by any municipality
- ✅ View all deposits and categories
- ✅ Manage all deposit categories

---

## 🛠 Technical Stack

### Frontend
- **Alpine.js** - State management
- **Tailwind CSS** - Styling
- **Chart.js** - Data visualization
- **Material Icons** - UI Icons

### Backend
- **Flask** - Web framework
- **Firestore** - Database
- **Xendit API** - Payment gateway

### Payment Gateway
- **Xendit** - Handles all payment processing
- Methods: Credit Card, Bank Transfer, E-wallets
- Webhooks for transaction updates

---

## 📝 Audit Trail

All transactions include:
- ✅ User ID + Email
- ✅ Invoice ID (Internal)
- ✅ External ID (Xendit reference)
- ✅ Timestamp (created_at, paid_at)
- ✅ Status history
- ✅ Payment method used
- ✅ Amount
- ✅ Municipality + Region scope

---

## 🚀 Next Steps / Enhancements

1. **Add National Admin View** - Create aggregate payment dashboard
2. **Payment Categories Management** - Link categories to deposits
3. **Tax Reporting** - Generate tax reports by category
4. **Reconciliation** - Match Xendit transactions with Firestore records
5. **Bulk Operations** - Batch process collections
6. **Advanced Filtering** - Date ranges, amount ranges
7. **API Webhooks** - Real-time payment status updates


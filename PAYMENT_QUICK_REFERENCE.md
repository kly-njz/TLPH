# 💰 DENR TLPH Payment System - Quick Reference

## 📚 Documentation Files Created

Three comprehensive documents have been created in the project root:

1. **PAYMENT_SYSTEM_OVERVIEW.md** ← START HERE
   - High-level architecture
   - Payment flow diagram
   - Data models
   - What each user role can do
   - Firestore collection schemas
   
2. **PAYMENT_ROUTES_REFERENCE.md**
   - Detailed endpoint documentation
   - Request/response examples
   - Authentication requirements
   - Error codes
   - Data flow walkthrough

3. **PAYMENT_FILES_INVENTORY.md**
   - Complete file listing
   - What each file does
   - Code locations with line numbers
   - Quick lookup guide
   - Implementation checklist

---

## 🎯 Quick Navigation

### I want to understand the payment system
→ Read **PAYMENT_SYSTEM_OVERVIEW.md**

### I need to call an API endpoint
→ Read **PAYMENT_ROUTES_REFERENCE.md**

### I need to find specific code
→ Read **PAYMENT_FILES_INVENTORY.md**

### I need to add a new feature
→ Check implementation checklist in PAYMENT_FILES_INVENTORY.md

---

## 📋 Payment System at a Glance

### User Level (Citizens)
```
Service Application → Payment Form → Xendit Checkout → Success/Failed Page
```
- **Frontend**: `templates/payment-form.html`
- **Backend**: `routes/payments_routes.py`
- **Database**: Firestore `transactions` collection

### Municipal Admin
```
Dashboard → Filter Payments → View Details → Download CSV
```
- **Frontend**: `templates/municipal/accounting/payment-deposits-municipal.html`
- **Backend**: `routes/municipal_api_logs.py` (lines 379-480)
- **Endpoint**: `GET /api/municipal/deposits/payments`
- **Scope**: Municipality only

### Regional Admin
```
Dashboard → Filter by Municipality → View Deposits → Manage Categories
```
- **Frontend**: `templates/regional/accounting/deposit-category-regional.html`
- **Backend**: `routes/regional_routes.py` (lines 2300-2450)
- **Endpoint**: `GET /regional/api/deposits/payments`
- **Scope**: Region + Municipalities

### National Admin (TODO)
```
Aggregate Dashboard → Filter by Region/Municipality → Export All Data
```
- **Frontend**: NOT YET CREATED
- **Backend**: NOT YET CREATED
- **Endpoint**: NOT YET CREATED
- **Scope**: All regions and municipalities

---

## 🔑 Key Files at a Glance

### Frontend Templates
| Location | Purpose | Role |
|----------|---------|------|
| `templates/payment-form.html` | Payment input form | User |
| `templates/payment-success.html` | Success page | User |
| `templates/payment-failed.html` | Failure page | User |
| `templates/user/transaction.html` | Service selection | User |
| `templates/user/transaction-history.html` | Payment history | User |
| `templates/municipal/accounting/payment-deposits-municipal.html` | Deposits view | Municipal |
| `templates/regional/accounting/deposit-category-regional.html` | Deposits + categories | Regional |

### Backend Routes
| File | Lines | Purpose |
|------|-------|---------|
| `routes/main_routes.py` | 416-424 | Success/Failed pages |
| `routes/payments_routes.py` | 1-641 | Xendit integration |
| `routes/municipal_api_logs.py` | 379-480 | Municipal deposits |
| `routes/regional_routes.py` | 2300-2450 | Regional deposits |
| `routes/national_routes.py` | TODO | National aggregate (NOT DONE) |

### Database
| Collection | Purpose | Indexed |
|-----------|---------|---------|
| `transactions` | Payment records | status, municipality, region |
| `users` | User info | email, municipality, region |

---

## 🔄 Data Flow Summary

```
┌─────────────┐
│ User Pays   │
│ via Xendit  │
└──────┬──────┘
       │
       ▼
┌─────────────────────────────┐
│ POST /api/payments/          │
│ record-transaction          │
└──────┬──────────────────────┘
       │
       ▼
┌─────────────────────────────┐
│ Firestore transactions      │
│ collection                  │
│ (one document per payment)  │
└──────┬──────────────────────┘
       │
    ┌──┴───────────────────────────────────┐
    │                                       │
    ▼                                       ▼
┌─────────────────────────┐   ┌─────────────────────────┐
│ Municipal Admin         │   │ Regional Admin          │
│ GET /api/municipal/     │   │ GET /regional/api/      │
│ deposits/payments       │   │ deposits/payments       │
│ (Scope: Municipality)   │   │ (Scope: Region)         │
└─────────────────────────┘   └─────────────────────────┘
    │                                   │
    ▼                                   ▼
┌─────────────────────────┐   ┌─────────────────────────┐
│ View in:                │   │ View in:                │
│ payment-deposits-       │   │ deposit-category-       │
│ municipal.html          │   │ regional.html           │
│ Tables + Charts         │   │ Tables + Charts         │
│ Filters + Export        │   │ Filters + Export        │
└─────────────────────────┘   └─────────────────────────┘
```

---

## 🚀 Endpoints Summary

### Public/Unauthenticated
```
POST   /api/payments/create-invoice          → Create Xendit invoice
POST   /api/payments/record-transaction      → Store transaction
GET    /api/payments/invoice-status/<id>     → Check payment status
GET    /api/payments/receipt/<id>            → Download PDF
GET    /payment-success                      → Show success page
GET    /payment-failed                       → Show failure page
```

### Municipal Admin Only
```
GET    /api/municipal/deposits/payments      → Get municipality payments
```

### Regional Admin Only
```
GET    /regional/api/deposits/payments       → Get region payments
```

### National Admin Only (TODO)
```
GET    /api/national/deposits/payments       → Get all payments
GET    /accounting/payments                  → Render national dashboard
```

---

## 📊 Statistics Tracked

### Per Transaction
- Invoice ID
- Amount (₱)
- Payer email
- Payment method (Credit Card, Bank Transfer)
- Status (Paid, Pending, Failed)
- Timestamp (created, paid)
- Municipality & Region

### Municipal Dashboard
- Total Deposits (sum of all payments)
- Payment Count (number of transactions)
- Completed Payments (count)
- Pending Amount (not yet paid)

### Regional Dashboard
- Total Paid Amount (₱)
- Paid Transactions Count
- Unique Payers Count
- Distribution by municipality
- Distribution by status

### National Dashboard (TODO)
- Aggregate by region
- Top municipalities
- Payment trends
- Method breakdown

---

## 🔐 Who Can See What?

```
User (Citizen)
├─ See own transactions
├─ Make payments
└─ Download own receipt

Municipal Admin
├─ See all payments from their municipality ✅
├─ Filter by status/payer
├─ Export CSV
└─ Cannot see other municipalities ✅

Regional Admin
├─ See all payments from their region ✅
├─ Filter by municipality/status/payer
├─ Export CSV
└─ Cannot see other regions ✅

National Admin
├─ See all payments everywhere ❌ (TODO)
├─ Filter by region/municipality
├─ Export all data
└─ Rights: Read-only

Super Admin
├─ Full access
├─ Manage all categories
├─ System settings
└─ Rights: Admin
```

---

## 🛠️ Implementation Status

### ✅ Complete and Working
- [x] User payment form + Xendit integration
- [x] Transaction recording to Firestore
- [x] Municipal deposits view (frontend + backend)
- [x] Payment success/failed pages
- [x] User transaction history

### ⚠️ Partial/Needs Testing
- [ ] Regional deposits view (frontend done, backend exists but untested)
- [ ] Regional category management (frontend only, no backend)

### ❌ Not Yet Implemented
- [ ] National admin payment dashboard
- [ ] Payment reconciliation
- [ ] Refund tracking
- [ ] Xendit webhook integration (real-time updates)
- [ ] Advanced reporting by category

---

## 🎓 Learning Path

### New Developer? Follow this path:

1. **Understand the Architecture**
   - Read: PAYMENT_SYSTEM_OVERVIEW.md
   - Time: 15 minutes

2. **See How Data Flows**
   - Read: PAYMENT_ROUTES_REFERENCE.md → "Data Flow" section
   - Time: 10 minutes

3. **Find Specific Code**
   - Use: PAYMENT_FILES_INVENTORY.md
   - Search for "Where is..." sections
   - Time: 5 minutes per lookup

4. **Test an Endpoint**
   - Use: PAYMENT_ROUTES_REFERENCE.md → "Request/Response Examples"
   - Test with curl or Postman
   - Time: 10 minutes

5. **Add a New Feature**
   - Check: PAYMENT_FILES_INVENTORY.md → "Implementation Checklist"
   - Follow existing pattern
   - Time: Varies

---

## 📞 Common Questions

### "How do I see the payments a municipal admin sees?"
→ Send GET `/api/municipal/deposits/payments` with municipal_admin auth token

### "How does the payment form get the amount?"
→ It's passed via service_type query parameter, or user enters manually

### "Where does the payment_method come from?"
→ User selects in payment-form.html (Credit Card, Bank Transfer)

### "Can a regional admin see a specific municipality's payments?"
→ Yes! Use municipality filter in deposit-category-regional.html

### "How are payments stored?"
→ Firestore `transactions` collection with full audit trail

### "What happens if payment fails?"
→ Transaction status = "failed", user redirected to payment-failed.html

### "Can users download a receipt?"
→ Yes! PDF generated via `/api/payments/receipt/<invoice_id>`

---

## 🚨 Known Issues & Todos

```
[ ] Regional deposits endpoint exists but may need testing
[ ] National admin view not implemented
[ ] Deposit category modal has no backend (demo only)
[ ] Xendit webhook integration not implemented
[ ] No refund tracking yet
[ ] Advanced filters (date range, amount range) not implemented
```

---

## 📈 Next Priority Features

1. **National Admin Dashboard** (High Priority)
   - Aggregate view of all payments
   - Filter by region/municipality
   - Export all data

2. **Real-time Updates** (Medium Priority)
   - Implement Xendit webhooks
   - Auto-update transaction status
   - Push notifications on payment

3. **Advanced Reporting** (Medium Priority)
   - Group by category
   - Date range reports
   - Tax summary reports

4. **Reconciliation Tools** (High Priority)
   - Match Xendit records with Firestore
   - Resolve discrepancies
   - Audit trail export

---

## 📞 Support

For questions about:
- **Architecture**: See PAYMENT_SYSTEM_OVERVIEW.md
- **APIs**: See PAYMENT_ROUTES_REFERENCE.md
- **File locations**: See PAYMENT_FILES_INVENTORY.md
- **Code changes**: Check git log or contact team lead

---

**Last Updated:** 2026-03-06  
**System Status:** 70% Complete  
**Performance:** Optimized for regions with <10k transactions  
**Next Review:** After National Admin implementation  


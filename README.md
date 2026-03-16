# TLPH — DENR E-Services Portal

A multi-tier government e-services web portal for the **Department of Environment and Natural Resources (DENR) of the Philippines**. Citizens can apply for environmental permits and licenses online, while DENR staff at the municipal, regional, national, and super-admin levels process, approve, and track those applications through a structured workflow.

![DENR](static/daily-tribune_import_wp-content_uploads_2022_12_DENR.avif)

---

## 📋 Project Overview

TLPH is a full-stack Flask web application backed by **Google Cloud Firestore** as the primary database and **Firebase Authentication** for identity management. It covers the complete lifecycle of DENR permit applications — from citizen submission and fee payment all the way through multi-level government review and final approval — while also providing integrated modules for Human Resource Management (HRM), Municipal Accounting, Inventory, System Logs, and a DENR-branded document print/PDF system.

### 🌐 Application Details

| Property | Value |
|---|---|
| Frontend | HTML5, CSS3, JavaScript (ES6+) |
| Backend | Flask 3.0 (Python 3.8+) |
| Database | Google Cloud Firestore (NoSQL) |
| Authentication | Firebase Auth (Pyrebase4 client-side + Firebase Admin server-side) |
| Storage | Firebase Cloud Storage |
| Payment Gateway | Xendit (Philippine fintech) |
| Email Service | Flask-Mail with Gmail SMTP |
| PDF Generation | ReportLab |
| Host / Port | `0.0.0.0:5000` |

---

## 🛠️ Technology Stack

| Package | Version | Purpose |
|---|---|---|
| `Flask` | 3.0.0 | Web framework |
| `firebase-admin` | 6.4.0 | Server-side Firestore & Firebase Auth |
| `pyrebase4` | 4.7.1 | Client-side Firebase operations |
| `Flask-SQLAlchemy` | 3.1.1 | ORM (configured, Firestore is primary DB) |
| `Flask-Mail` | 0.9.1 | OTP email delivery |
| `python-dotenv` | 1.0.0 | `.env` configuration loading |
| `xendit` | 0.1.3 | Xendit payment gateway SDK |
| `requests` | 2.29.0 | HTTP calls to Xendit API |
| `reportlab` | 4.0.4 | PDF receipt and document generation |
| `python-calendar` | 1.0.1 | Calendar utilities for HRM payroll |
| `setuptools` | 68.0.0 | Build tools |

---

## 👥 User Roles & Access Hierarchy

| Role | Dashboard URL | Description |
|---|---|---|
| `user` | `/user/dashboard` | Citizen — applies for permits, pays fees |
| `municipal` / `municipal_admin` | `/municipal/dashboard` | Municipal DENR office staff |
| `regional` / `regional_admin` | `/regional/profile` | Regional DENR office staff |
| `national` / `national_admin` | `/national/dashboard` | National DENR headquarters |
| `super-admin` / `superadmin` | `/superadmin/inventory` | System super-administrator |

Role-based access control is enforced server-side on every route via the `@role_required(...)` decorator in `firebase_auth_middleware.py`. Unauthenticated requests redirect to login; wrong-role requests redirect to the user's own dashboard.

---

## ✨ Features

### 🔑 Authentication & Security
- **Firebase Authentication** (via Pyrebase4) for login; server Flask session set via `/api/set-session`
- **Email OTP verification** on registration — 6-digit code with 10-minute expiry
- Role-based access control enforced on every route with `@role_required`
- Disabled account detection before rendering any page
- Cache-control headers (`no-store`) on all protected pages to prevent back-button access
- Environment variable isolation for all secrets (`.env` + `firebase-credentials.json`)

### 📜 Permits & Licenses (36+ application types across 6 domains)

| Domain | Application Types |
|---|---|
| **Environment** | Environmental Compliance Certificate (ECC), Waste Management, Water Use, Hazardous Materials, CCO, PCL, Permit to Operate (Air), PICCS, Water Disposal, Hazardous Waste Generator |
| **Fisheries** | Aquafarm, Fish Transport, Fish Dealer, Processing, Harvest |
| **Forest** | Tree-Cutting, Timber, Reforestation, Nursery, Non-Timber Forest Products, Tree Planting |
| **Livestock** | Animal Transport, Meat Transport, Slaughterhouse, Poultry Farm, Animal Health |
| **Wildlife** | Wildlife Ownership, Transport, Collection, Wildlife Farm |
| **General Permits** | Export, Operation, Import, Wildlife Trade, Local Transport, Harvest |

### 🔄 Multi-Tier Application Workflow
Applications follow a staged approval pipeline across all government levels:

```
User submits (pending)
    └─► Municipal Admin reviews → "to review"
            └─► Regional Admin approves → "approved" (regional)
                    └─► National Admin gives final approval → "nationalStatus: approved"
```

### 🛎️ Services
- **Farm Visit Services**: Initial visit, compliance, disease, soil, general visit
- **Fertilizer Services**: Input usage, chemical registration, emergency pest control, fertilizer/pesticide recommendations
- **Financial Services**: Subsidy, grant, loan, crop insurance, startup support
- **Compensation**: Typhoon disaster / pest damage compensation requests
- **Seminars & Training**: GAP training, pest/disease management, safe pesticide handling, nursery/propagation, regulatory compliance orientation

### 💳 Payment System (Xendit)
- Creates **Xendit invoices** for permit and license application fees
- **Webhook receiver** automatically updates Firestore transaction status on payment confirmation
- **PDF receipt generation** via ReportLab (downloadable)
- Transaction history visible at every role level (scoped to municipality / region / national)
- Payment statistics (total deposits, paid / pending / failed) on all dashboards

### 🧑‍💼 Human Resource Management (HRM) Module
Available at municipal level and above:
- **Company, Department & Designation** management
- **Employee records** (hire date, designation, department, contact info)
- **Attendance** tracking and office shift scheduling
- **Leave request** management (file, approve, reject)
- **Payroll** computation and payslip generation
- **Holiday calendar** management

### 📒 Municipal Accounting Module
- **Chart of Accounts (COA)** templates and individual account entries per municipality
- **Entities** (offices, banks, organizational units)
- **Deposit categories** — linked to COA codes and revenue types
- **Expense categories** — organized by office and fund type
- Accounting dashboard with financial summary statistics
- Payment deposit recording and reconciliation

### 📦 Inventory Management
- Stock tracking per municipality/region/national level
- Stock history and movement reporting
- User-facing stock list view

### 🖨️ DENR Print & PDF System
- Official DENR-branded print styling (`denr-print.css`) with DENR green header
- Government document formatting with signature sections, security watermarks, and barcode-style reference numbers
- ReportLab-based PDF export for receipts and official documents
- Print preview page (`denr-print-preview.html`)

### 📋 System & Audit Logs
- Comprehensive action logging: login events, CRUD operations, account creation/disablement
- Logs stored in `system_logs` (municipal-scoped) and `regional_system_logs` (region-scoped) Firestore collections
- Device type detection (mobile / tablet / desktop) from User-Agent
- **180-day TTL retention** with automatic cleanup
- Accessible at municipal, regional, and super-admin levels with appropriate scope filtering

### 🗺️ Philippine Location Data
- Complete `models/ph_locations.py` mapping all Philippine provinces to their municipalities
- Used in dropdowns throughout the system for location-based filtering and scoping

---

## 📁 Project Structure

```
TLPH/
├── app.py                          # Main Flask application entry point
├── config.py                       # App configuration (session, mail, Firebase)
├── firebase_config.py              # Firebase Admin + Pyrebase initialization
├── firebase_auth_middleware.py     # Role-based access control decorator
│
├── transaction_storage.py          # Payment transactions & finance records (Firestore)
├── deposit_storage.py              # Municipal deposit/revenue categories
├── expense_storage.py              # Municipal expense categories
├── coa_storage.py                  # Chart of Accounts templates and account entries
├── entities_storage.py             # Municipal entities (offices, banks, units)
├── system_logs_storage.py          # Audit/activity logs with TTL management
│
├── routes/
│   ├── main_routes.py              # Auth, home, national dashboard
│   ├── api_routes.py               # REST API (OTP, register, login, applications)
│   ├── municipal_routes.py         # Municipal admin UI (HRM, accounting, operations)
│   ├── regional_routes.py          # Regional admin UI
│   ├── national_routes.py          # National admin UI
│   ├── superadmin_routes.py        # Super-admin UI
│   ├── municipal_api_logs.py       # Municipal data API (transactions, payroll, COA…)
│   ├── payments_routes.py          # Xendit invoice creation, webhook, PDF receipt
│   ├── permits_routes.py           # General permit applications (user)
│   ├── environment_routes.py       # Environmental clearance applications
│   ├── fisheries_routes.py         # Fisheries license applications
│   ├── forest_routes.py            # Forest resource license applications
│   ├── livestock_routes.py         # Livestock license applications
│   ├── wildlife_routes.py          # Wildlife license applications
│   ├── farm_routes.py              # Farm visit service requests
│   ├── service_routes.py           # General services (fertilizer, financial, compensation)
│   └── seminar_routes.py           # Seminar/training registrations
│
├── models/
│   ├── __init__.py
│   └── ph_locations.py             # Full Philippine province-to-municipality mapping
│
├── templates/
│   ├── home.html, login.html, signup.html
│   ├── create-municipal-admin.html
│   ├── create_regional_account.html
│   ├── payment-form.html, payment-success.html, payment-failed.html
│   ├── denr-print-preview.html
│   ├── account-disabled.html, auth_check.html, approval_status.html
│   ├── user/                       # Citizen portal (dashboard, profile, applications, permits, services)
│   ├── municipal/                  # Municipal admin (HRM, accounting, operations, logs)
│   ├── regional/                   # Regional admin (scoped dashboards, HR, accounting)
│   ├── national/                   # National admin (operations, HRM, logistics)
│   └── super-admin/                # Super-admin (global management, finance, regions)
│
├── static/
│   ├── css/                        # Stylesheets (auth, dashboard, denr-print, regional, seminar…)
│   ├── js/                         # JavaScript files
│   ├── images/                     # Image assets
│   └── uploads/                    # User-uploaded files
│
├── requirements.txt
├── firebase-credentials.json       # Firebase service account key (not committed)
└── .env                            # Environment variables (not committed)
```

---

## 🚀 Getting Started

### Prerequisites

```
Python 3.8+
pip
Firebase project (Firestore + Authentication + Storage)
Xendit account
Gmail account with App Password enabled
```

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/alqzdave/TLPH.git
   cd TLPH
   ```

2. **Create and activate a virtual environment**
   ```bash
   python -m venv .venv
   .venv\Scripts\activate        # Windows
   source .venv/bin/activate     # macOS/Linux
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables** — create a `.env` file in the root directory:
   ```env
   SECRET_KEY=your-secret-key
   MAIL_USERNAME=your-gmail@gmail.com
   MAIL_PASSWORD=your-app-password
   FIREBASE_API_KEY=your-firebase-api-key
   FIREBASE_AUTH_DOMAIN=your-project.firebaseapp.com
   FIREBASE_DATABASE_URL=https://your-project.firebaseio.com
   FIREBASE_PROJECT_ID=your-project-id
   FIREBASE_STORAGE_BUCKET=your-project.appspot.com
   FIREBASE_MESSAGING_SENDER_ID=your-sender-id
   FIREBASE_APP_ID=your-app-id
   XENDIT_API_KEY=your-xendit-api-key
   XENDIT_PUBLIC_KEY=your-xendit-public-key
   ```

5. **Place Firebase credentials**
   - Download your service account key from the Firebase Console
   - Save it as `firebase-credentials.json` in the root directory

6. **Run the application**
   ```bash
   # Always use the virtual environment Python
   .venv\Scripts\python.exe app.py
   ```
   > **Note**: Using `.venv\Scripts\python.exe` ensures all dependencies from the virtual environment are available. `py app.py` or `python app.py` may fail with import errors if the system Python is picked up instead.

7. **Open the application**
   ```
   http://localhost:5000
   ```

---

## 📧 Email Configuration

The application uses Gmail SMTP for OTP verification emails. To configure:

1. Enable 2-Factor Authentication on your Gmail account
2. Generate an App Password (Google Account → Security → App Passwords)
3. Add to `.env`:
   ```env
   MAIL_USERNAME=your-email@gmail.com
   MAIL_PASSWORD=your-app-password
   ```

---

## 📊 API Endpoints

| Category | Base Path | Key Endpoints |
|---|---|---|
| Auth | `/api` | `POST /api/send-otp`, `POST /api/verify-otp`, `POST /api/register`, `POST /api/login`, `POST /api/logout` |
| Session | `/api` | `POST /api/set-session` |
| Applications | `/api` | CRUD for permit applications, service requests |
| Payments | `/api/payments` | `POST /create-invoice`, `POST /webhook`, `GET /status/<id>`, `GET /history`, `POST /generate-receipt` |
| Municipal Data | `/api/municipal` | Transactions, deposits, expenses, COA, entities, employees, payroll, leave, system logs |

---

## 🔐 Security Features

- Firebase Authentication with secure token management
- Server-side role enforcement (`@role_required`) on every protected route
- Email OTP with 10-minute expiry for registration verification
- All secrets isolated in `.env` (never hardcoded)
- Cache-control `no-store` headers prevent cached access after logout
- Disabled account detection at every page load
- Input validation at system boundaries (API routes and form handlers)
- HTTPS-ready for production deployment

---

## 🚀 Deployment

### Local Development
```bash
.venv\Scripts\python.exe app.py
# Runs on http://localhost:5000 with debug mode enabled
```

### Production
1. Set `debug=False` in `app.py`
2. Configure all production environment variables in `.env`
3. Use a production WSGI server (e.g., Gunicorn or Waitress)
4. Set up HTTPS with SSL/TLS certificates
5. Switch Firebase and Xendit to their production configurations
6. Enable Firestore indexes as documented in [REGIONAL_SYSTEM_LOGS_OPERATIONS.md](REGIONAL_SYSTEM_LOGS_OPERATIONS.md)

---

## 🔧 Troubleshooting

| Problem | Solution |
|---|---|
| **Port 5000 already in use** | `netstat -ano \| findstr :5000` then `taskkill /PID <id> /F` |
| **Firebase connection error** | Verify `.env` credentials and confirm `firebase-credentials.json` is in the root |
| **Missing module / ImportError** | Run `pip install -r requirements.txt` inside the virtual environment |
| **Email OTP not sending** | Confirm Gmail App Password is correct and 2FA is enabled on the account |
| **Payment integration issues** | Verify Xendit API keys and check whether test or production keys are configured |
| **File upload errors** | Check Firebase Storage permissions and storage bucket config in `.env` |
| **Firestore permission denied** | Verify Firestore security rules allow the operation for the authenticated user's role |

---

## 📁 Project Structure

```
TLPH/
├── app.py
├── config.py
├── firebase_config.py
├── firebase_auth_middleware.py
├── transaction_storage.py
├── deposit_storage.py
├── expense_storage.py
├── coa_storage.py
├── entities_storage.py
├── system_logs_storage.py
├── requirements.txt
├── .env                            # (not committed)
├── firebase-credentials.json       # (not committed)
│
├── routes/                         # All Flask blueprints
├── models/                         # ph_locations.py
├── templates/                      # Jinja2 HTML templates per role
└── static/                         # CSS, JS, images, uploads
```

---

## 👥 Contributors

### Development Team

| Name | Role | Email | GitHub |
|---|---|---|---|
| Mark Dave Alquiza | Team Lead | markdavemarasiganalquiza@gmail.com | [@alqzdave](https://github.com/alqzdave) |
| Aerone John Grefalda | Frontend Developer | grefaldaaeronejohn01@gmail.com | [@Aerone01](https://github.com/Aerone01) |
| John Cedric Acapulco | Frontend Developer | acapulcojohncedric66@gmail.com | [@Cheezzyy1](https://github.com/Cheezzyy1) |
| Jhon Carlo Jimenez | Backend Developer | jimenez.jhoncarlo@minsu.edu.ph | [@kly-njz](https://github.com/kly-njz) |
| John Mark Pagaduan | Q/A, Developer | pagaduanjohnmark29@gmail.com | [@johnmark009](https://github.com/johnmark009) |
| Huriecane Ivan Ganio | Q/A, Developer | hurieganio@gmail.com | [@Huriecane](https://github.com/Huriecane) |

Special thanks to the **DENR TLPH Team** for their support and guidance throughout the development of this project.

---

## 🤝 Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

**Contribution guidelines:**
- Follow the existing code style and blueprint structure
- Write descriptive commit messages
- Test changes at all affected role levels
- Update relevant documentation files as needed
- Ensure Firebase and Xendit integrations are properly tested before submitting

---

## 📚 Setup Guides

- [Firebase Setup Guide](FIREBASE_SETUP_GUIDE.md)
- [Firebase Setup Instructions](FIREBASE_SETUP.md)
- [Firebase Transactions Setup](FIREBASE_TRANSACTIONS_SETUP.md)
- [Xendit Payment Integration](XENDIT_SETUP.md)
- [Payment System Overview](PAYMENT_SYSTEM_OVERVIEW.md)
- [DENR Print System](DENR_PRINT_SYSTEM.md)
- [Regional System Logs Operations](REGIONAL_SYSTEM_LOGS_OPERATIONS.md)
- [Companies Schema](COMPANIES_SCHEMA.md)
- [Departments Schema](DEPARTMENTS_SCHEMA.md)
- [Designations & Employees Schema](DESIGNATIONS_EMPLOYEES_SCHEMA.md)

---

## 📞 Contact & Support

- **Issue Tracker**: [Open an issue on GitHub](https://github.com/alqzdave/TLPH/issues)
- **Lead Developer**: Mark Dave Alquiza — markdavemarasiganalquiza@gmail.com
- **Repository**: [https://github.com/alqzdave/TLPH](https://github.com/alqzdave/TLPH)
- **Organization**: DENR TLPH Team

When reporting bugs please include: a description of the issue, steps to reproduce, expected vs. actual behavior, screenshots if applicable, and your browser/OS.

---

## 🎯 Planned Enhancements

- [ ] Mobile application (iOS / Android)
- [ ] SMS notifications
- [ ] Advanced analytics dashboard
- [ ] Automated scheduled report generation
- [ ] Multi-language support (Filipino / English)
- [ ] Offline mode capability
- [ ] Data export (CSV / Excel)
- [ ] Enhanced search and filtering across all modules

---

## 📄 License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.

---

## 📖 Additional Resources

- [Flask Documentation](https://flask.palletsprojects.com/)
- [Firebase Documentation](https://firebase.google.com/docs)
- [Xendit API Documentation](https://xendit.io/docs)
- [Python-dotenv Documentation](https://pypi.org/project/python-dotenv/)
- [ReportLab Documentation](https://www.reportlab.com/docs/reportlab-userguide.pdf)

## 🏆 Acknowledgments

- **DENR (Department of Environment and Natural Resources)** - Project sponsor and stakeholder
- **Firebase** - Backend infrastructure and authentication
- **Xendit** - Payment gateway integration
- **Flask Community** - Web framework and ecosystem
- All contributors and team members who made this project possible

## 📜 Version History

- **v1.0** - Initial release with core features
  - User authentication and authorization
  - License and permit management
  - Payment integration
  - Inventory tracking
  - Transaction management

---

**Made with ❤️ by the DENR TLPH Development Team**

For more information or to contribute, visit our [GitHub Repository](https://github.com/alqzdave/TLPH)

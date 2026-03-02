# HR Management - Designations & Employees Data Structure

## Overview
This document defines the Firestore collections structure for DENR's HR Management system, separating **Designations** (position definitions) from **Employees** (personnel records).

---

## Collection: `designations`

**Purpose:** Stores official position/role definitions with authority levels, qualifications, and pay structures.

### Fields

| Field | Type | Required | Description | Example |
|-------|------|----------|-------------|---------|
| `designation` | string | ✓ | Official position title | "Field Officer" |
| `Department_name` | string | ✓ | Primary department | "TECHNICAL OPERATIONS BUREAU" |
| `division` | string | ✓ | Sub-division/unit | "Field Operations" |
| `description` | string | ✓ | Duties and responsibilities | "Responsible for field inspections..." |
| `required_qualifications` | string | - | Education and experience requirements | "Bachelor's degree in Environmental Science..." |
| `basic_pay` | number | ✓ | Standard salary for position | 35000 |
| `duty_type` | string | ✓ | Work schedule type | "field duty", "fixed office hours", "flexible" |
| `overtime_status` | string | ✓ | OT eligibility | "eligible", "exempt" |
| `authority_level` | string | - | Signing/approval authority | "Field Authorization - Level 2" |
| `field_service` | string | - | Field work requirement | "Required - 80% field work" |
| `status` | string | ✓ | Current status | "Active", "Archived" |
| `municipality` | string | - | Geographic scope | "Naujan", "All", "Region-wide" |
| `refField_title` | string | - | Reference category | "Environmental Field Operations" |
| `time_Init` | timestamp | ✓ | Creation timestamp | SERVER_TIMESTAMP |
| `created_by` | string | - | Creator reference | "admin@denr.gov.ph" |

### Example Document

```json
{
  "designation": "Field Officer",
  "Department_name": "TECHNICAL OPERATIONS BUREAU",
  "division": "Field Operations",
  "description": "Responsible for field inspections, environmental assessments, and on-site compliance monitoring.",
  "required_qualifications": "Bachelor's degree in Environmental Science, Forestry, or related field. Minimum 2 years field experience.",
  "basic_pay": 35000,
  "duty_type": "field duty",
  "overtime_status": "eligible",
  "authority_level": "Field Authorization - Level 2",
  "field_service": "Required - 80% field work",
  "status": "Active",
  "municipality": "Naujan",
  "refField_title": "Environmental Field Operations",
  "time_Init": "2026-03-01T10:30:00Z",
  "created_by": "System Migration"
}
```

---

## Collection: `employees`

**Purpose:** Stores individual personnel records with employment details and current status.

### Fields

| Field | Type | Required | Description | Example |
|-------|------|----------|-------------|---------|
| `employee_id` | string | ✓ | Unique employee identifier | "EMP-0001" |
| `first_name` | string | ✓ | First name | "Juan" |
| `middle_name` | string | - | Middle name | "Dela" |
| `last_name` | string | ✓ | Last name | "Cruz" |
| `designation` | string | ✓ | **Links to designations.designation** | "Field Officer" |
| `department_name` | string | ✓ | Current department assignment | "TECHNICAL OPERATIONS BUREAU" |
| `division` | string | - | Current division | "Field Operations" |
| `municipality` | string | ✓ | Assigned municipality | "Naujan" |
| `province` | string | ✓ | Province | "Oriental Mindoro" |
| `region` | string | ✓ | Region | "MIMAROPA" |
| `contact_Number` | string | - | Phone number | "09171234567" |
| `email` | string | ✓ | Official email | "juan.delacruz@denr.gov.ph" |
| `hire_date` | timestamp | ✓ | Date hired | "2024-02-19" |
| `status` | string | ✓ | Employment status | "Active", "Inactive", "On Leave" |
| `attendance_status` | string | - | Current attendance | "On Duty", "On Field", "Absent" |
| `basic_pay` | number | ✓ | Current salary | 35000 |
| `allowances` | number | - | Monthly allowances | 8000 |
| `duty_type` | string | ✓ | Work schedule (from designation) | "field duty" |
| `overtime_status` | string | - | OT eligibility | "eligible" |
| `office_address` | string | - | Primary office location | "DENR Provincial Office, Calapan City" |
| `municipal_address` | string | - | Municipality office | "Naujan Municipal Office" |
| `role` | string | ✓ | System role | "municipal", "regional", "national" |
| `refField_title` | string | - | Field specialty | "Environmental Field Operations" |
| `time_in` | timestamp | - | Clock-in time | null or timestamp |
| `time_out` | timestamp | - | Clock-out time | null or timestamp |
| `leaves_taken` | number | - | Days of leave used | 0 |
| `rated_status` | string | - | Performance rating | "Outstanding", "Satisfactory" |
| `time_Init` | timestamp | ✓ | Record creation | SERVER_TIMESTAMP |

### Example Document

```json
{
  "employee_id": "EMP-0001",
  "first_name": "Juan",
  "middle_name": "Dela",
  "last_name": "Cruz",
  "designation": "Field Officer",
  "department_name": "TECHNICAL OPERATIONS BUREAU",
  "division": "Field Operations",
  "municipality": "Naujan",
  "province": "Oriental Mindoro",
  "region": "MIMAROPA",
  "contact_Number": "09171234567",
  "email": "juan.delacruz@denr.gov.ph",
  "hire_date": "2024-02-19T00:00:00Z",
  "status": "Active",
  "attendance_status": "On Duty",
  "basic_pay": 35000,
  "allowances": 8000,
  "duty_type": "field duty",
  "overtime_status": "eligible",
  "office_address": "DENR Provincial Office, Calapan City",
  "municipal_address": "Naujan Municipal Office",
  "role": "municipal",
  "refField_title": "Environmental Field Operations",
  "time_in": null,
  "time_out": null,
  "leaves_taken": 0,
  "rated_status": "Satisfactory",
  "time_Init": "2026-03-01T10:30:00Z"
}
```

---

## Relationships

### Linking Employees to Designations

Employees are linked to Designations via the `designation` field (string match):

```javascript
// Get designation details
const designation = await db.collection('designations')
  .where('designation', '==', 'Field Officer')
  .limit(1)
  .get();

// Get all employees with this designation
const employees = await db.collection('employees')
  .where('designation', '==', 'Field Officer')
  .get();
```

### Query Examples

**1. Get all employees in a department:**
```javascript
const employees = await db.collection('employees')
  .where('department_name', '==', 'TECHNICAL OPERATIONS BUREAU')
  .where('status', '==', 'Active')
  .get();
```

**2. Get designation with employee count:**
```javascript
const designation = await db.collection('designations').doc(id).get();
const employees = await db.collection('employees')
  .where('designation', '==', designation.data().designation)
  .get();
  
console.log(`${designation.data().designation}: ${employees.size} employees`);
```

**3. Filter employees by municipality and status:**
```javascript
const employees = await db.collection('employees')
  .where('municipality', '==', 'Naujan')
  .where('status', '==', 'Active')
  .orderBy('hire_date', 'desc')
  .get();
```

---

## Migration Steps

1. **Run migration script:**
   ```bash
   python migrate_designations_employees.py
   ```

2. **Verify collections in Firestore Console:**
   - Check `designations` collection
   - Check `employees` collection

3. **Test the designation-municipal.html page:**
   - Should display designations list
   - Should show employees for each designation
   - Filters should work properly

4. **Add your actual data:**
   - Use Firestore console or create admin forms
   - Follow the field structure documented above

---

## Admin Operations

### Adding a New Designation

```python
from firebase_admin import firestore

db = firestore.client()

new_designation = {
    'designation': 'Environmental Specialist',
    'Department_name': 'ENVIRONMENTAL MANAGEMENT',
    'division': 'Compliance Monitoring',
    'description': 'Conducts environmental impact assessments...',
    'required_qualifications': 'Master\'s degree in Environmental Science',
    'basic_pay': 42000,
    'duty_type': 'flexible',
    'overtime_status': 'eligible',
    'authority_level': 'Technical Review - Level 2',
    'field_service': 'Mixed duties',
    'status': 'Active',
    'municipality': 'Regional',
    'time_Init': firestore.SERVER_TIMESTAMP,
    'created_by': 'admin@denr.gov.ph'
}

db.collection('designations').add(new_designation)
```

### Adding a New Employee

```python
from datetime import datetime

new_employee = {
    'employee_id': 'EMP-0004',
    'first_name': 'Ana',
    'middle_name': 'Maria',
    'last_name': 'Santos',
    'designation': 'Environmental Specialist',  # Must match a designation
    'department_name': 'ENVIRONMENTAL MANAGEMENT',
    'municipality': 'Baco',
    'province': 'Oriental Mindoro',
    'region': 'MIMAROPA',
    'email': 'ana.santos@denr.gov.ph',
    'hire_date': datetime.now(),
    'status': 'Active',
    'basic_pay': 42000,
    'allowances': 9000,
    'role': 'municipal',
    'time_Init': firestore.SERVER_TIMESTAMP
}

db.collection('employees').add(new_employee)
```

---

## Security Rules (Firestore)

```javascript
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    
    // Designations - Read all, write for admins only
    match /designations/{designationId} {
      allow read: if request.auth != null;
      allow write: if request.auth.token.role in ['admin', 'superadmin'];
    }
    
    // Employees - Read all, write for admins and HR
    match /employees/{employeeId} {
      allow read: if request.auth != null;
      allow write: if request.auth.token.role in ['admin', 'superadmin', 'hr_admin'];
      
      // Employees can read their own record
      allow read: if request.auth.uid == resource.data.user_id;
    }
  }
}
```

---

## Notes

- **designation** field in employees collection MUST exactly match a designation name in designations collection
- Use `SERVER_TIMESTAMP` for `time_Init` to ensure consistency
- All currency values in Philippine Pesos (₱)
- Employee status values: "Active", "Inactive", "On Leave", "Retired", "Terminated"
- Designation status values: "Active", "Archived"

---

**Last Updated:** March 1, 2026  
**Maintained by:** DENR IT Team

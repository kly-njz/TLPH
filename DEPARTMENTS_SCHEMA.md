# Departments Collection Schema

## Overview
This document defines the Firestore `departments` collection structure for DENR's organizational departments/bureaus.

---

## Collection: `departments`

**Purpose:** Stores department/bureau organizational units with their mandate, location, and leadership information.

### Fields

| Field | Type | Required | Description | Example |
|-------|------|----------|-------------|---------|
| `department_name` | string | ✓ | Official department/bureau name | "TECHNICAL OPERATIONS BUREAU" |
| `department_code` | string | ✓ | Short code/acronym | "TOB" |
| `mandate` | string | ✓ | Primary responsibilities and scope | "Field operations, environmental assessments..." |
| `region` | string | ✓ | Geographic region | "MIMAROPA" |
| `municipality` | string | - | Municipality scope | "Regional", "Naujan", etc. |
| `office_location` | string | ✓ | Physical office address | "DENR Provincial Office, Calapan City..." |
| `head_of_department` | string | - | Current department head | "Engr. Roberto M. Santos" |
| `status` | string | ✓ | Operational status | "Active", "Inactive", "Restructuring" |
| `contact_email` | string | - | Official email address | "tob@denr.gov.ph" |
| `contact_number` | string | - | Contact phone number | "09171234567" |
| `established_date` | timestamp | - | Date established | datetime(2018, 1, 15) |
| `time_Init` | timestamp | ✓ | Record creation timestamp | SERVER_TIMESTAMP |
| `created_by` | string | - | Creator reference | "admin@denr.gov.ph" |

### Example Document

```json
{
  "department_name": "TECHNICAL OPERATIONS BUREAU",
  "department_code": "TOB",
  "mandate": "Field operations, environmental assessments, and technical compliance monitoring",
  "region": "MIMAROPA",
  "municipality": "Regional",
  "office_location": "DENR Provincial Office, Calapan City, Oriental Mindoro",
  "head_of_department": "Engr. Roberto M. Santos",
  "status": "Active",
  "contact_email": "tob@denr.gov.ph",
  "contact_number": "09171234567",
  "established_date": "2018-01-15T00:00:00Z",
  "time_Init": "2026-03-01T10:30:00Z",
  "created_by": "System Migration"
}
```

---

## Relationships

### Department → Employees

Employees belong to departments via the `department_name` field:

```javascript
// Get all employees in a department
const dept = await db.collection('departments').doc(deptId).get();
const employees = await db.collection('employees')
  .where('department_name', '==', dept.data().department_name)
  .get();

console.log(`${dept.data().department_name}: ${employees.size} employees`);
```

### Department → Designations

Designations can be filtered by department:

```javascript
// Get all designations in a department
const dept = await db.collection('departments').doc(deptId).get();
const designations = await db.collection('designations')
  .where('Department_name', '==', dept.data().department_name)
  .get();

console.log(`${dept.data().department_name}: ${designations.size} positions`);
```

---

## Complete Data Flow

```
departments (4 departments)
    ↓ department_name
employees (3 employees)
    ↓ designation
designations (3 positions)
```

**Example:**
1. **TECHNICAL OPERATIONS BUREAU** (department)
   - Has employee: **Juan Dela Cruz** (department_name = "TECHNICAL OPERATIONS BUREAU")
   - Employee has designation: **Field Officer**
   - Designation details in `designations` collection

---

## Query Examples

### 1. Get department with statistics

```javascript
const deptDoc = await db.collection('departments').doc(deptId).get();
const deptData = deptDoc.data();

// Get employee count
const employees = await db.collection('employees')
  .where('department_name', '==', deptData.department_name)
  .where('status', '==', 'Active')
  .get();

// Get designation count
const designations = await db.collection('designations')
  .where('Department_name', '==', deptData.department_name)
  .get();

console.log({
  department: deptData.department_name,
  employees: employees.size,
  designations: designations.size,
  head: deptData.head_of_department
});
```

### 2. List all departments with employee counts

```javascript
const departments = await db.collection('departments').get();
const employees = await db.collection('employees').get();

departments.forEach(dept => {
  const deptName = dept.data().department_name;
  const empCount = employees.docs.filter(emp => 
    emp.data().department_name === deptName && 
    emp.data().status === 'Active'
  ).length;
  
  console.log(`${deptName}: ${empCount} employees`);
});
```

### 3. Get divisions within a department

```javascript
const deptDoc = await db.collection('departments').doc(deptId).get();
const employees = await db.collection('employees')
  .where('department_name', '==', deptDoc.data().department_name)
  .get();

// Get unique divisions
const divisions = [...new Set(employees.docs.map(e => e.data().division).filter(Boolean))];
console.log(`Divisions: ${divisions.join(', ')}`);
```

---

## Admin Operations

### Adding a New Department

```python
from firebase_admin import firestore
from datetime import datetime

db = firestore.client()

new_department = {
    'department_name': 'WILDLIFE RESOURCES DIVISION',
    'department_code': 'WRD',
    'mandate': 'Wildlife conservation, protected areas management, biodiversity monitoring',
    'region': 'MIMAROPA',
    'municipality': 'Regional',
    'office_location': 'DENR Provincial Office, Calapan City, Oriental Mindoro',
    'head_of_department': 'Biologist Ramon P. Cruz',
    'status': 'Active',
    'contact_email': 'wildlife@denr.gov.ph',
    'contact_number': '09165432109',
    'established_date': datetime(2020, 7, 1),
    'time_Init': firestore.SERVER_TIMESTAMP,
    'created_by': 'admin@denr.gov.ph'
}

db.collection('departments').add(new_department)
```

### Updating Department Head

```python
dept_ref = db.collection('departments').document('dept_id_here')
dept_ref.update({
    'head_of_department': 'New Head Name',
    'updated_at': firestore.SERVER_TIMESTAMP,
    'updated_by': 'admin@denr.gov.ph'
})
```

---

## Integration with HR Pages

### department-municipal.html Features

1. **Department List** - Shows all departments with employee counts
2. **Department Details** - Displays full information for selected department
3. **Department Personnel** - Lists all employees in the department
4. **Filters** - Filter employees by division and status
5. **Statistics** - Shows employee count, designations, divisions

### Key Metrics Displayed

- Active employee count per department
- Number of designations/positions
- Number of divisions
- Department head
- Contact information
- Establishment date

---

## Data Validation Rules

```javascript
// Firestore Security Rules
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    
    match /departments/{departmentId} {
      // Read access for authenticated users
      allow read: if request.auth != null;
      
      // Write access for admin only
      allow create, update: if request.auth.token.role in ['admin', 'superadmin'] 
        && request.resource.data.department_name is string
        && request.resource.data.department_code is string
        && request.resource.data.status in ['Active', 'Inactive', 'Restructuring'];
      
      // Delete restricted
      allow delete: if request.auth.token.role == 'superadmin';
    }
  }
}
```

---

## Notes

- **department_name** must match exactly in employees.department_name and designations.Department_name
- Use **department_code** for short references in reports
- **status** values: "Active", "Inactive", "Restructuring"
- **municipality** can be "Regional" for region-wide departments
- Always use `SERVER_TIMESTAMP` for time_Init

---

## Sample Departments Created

1. **TECHNICAL OPERATIONS BUREAU** (TOB)
   - Field operations and technical compliance
   - 1 employee, 1 designation

2. **ADMINISTRATIVE DIVISION** (ADMIN)
   - Administrative support and HR
   - 1 employee, 1 designation

3. **FORESTRY SERVICES** (FS)
   - Forest management and reforestation
   - 1 employee, 1 designation

4. **ENVIRONMENTAL MANAGEMENT** (EMB)
   - Environmental assessments and pollution control
   - 0 employees, 0 designations (new department)

---

**Last Updated:** March 2, 2026  
**Maintained by:** DENR IT Team

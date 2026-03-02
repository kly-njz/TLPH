# Companies Collection Schema

## Overview
The `companies` collection stores information about municipal DENR offices and their administrative details.

## Collection: `companies`

### Document Structure

```json
{
  "office_name": "San Juan Del Monte DENR Office",
  "municipality": "San Juan Del Monte",
  "province": "Batangas",
  "region": "Region IV-A (CALABARZON)",
  "lgu_class": "1st Class Municipality",
  "physical_address": "Floor 2, Environmental Unit, New Government Center, Brgy. Poblacion, San Juan, Batangas",
  "email": "admin-sanjuan@denr-muni.gov.ph",
  "contact_number": "(+63) 43-552-1922",
  "office_hours": "8:00 AM - 5:00 PM (Monday-Friday)",
  "verification_status": "Authenticated",
  "linked_users": 1240,
  "pending_requests": 14,
  "active_programs": 8,
  "status": "Active",
  "created_at": "2024-10-15T10:20:30.000Z",
  "updated_at": "2024-10-24T16:45:00.000Z"
}
```

## Field Definitions

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `office_name` | String | Yes | Name of the DENR office |
| `municipality` | String | Yes | Municipality where office is located |
| `province` | String | Yes | Province of the municipality |
| `region` | String | No | Administrative region (e.g., Region IV-A) |
| `lgu_class` | String | Yes | Classification of the LGU (e.g., 1st Class, 2nd Class) |
| `physical_address` | String | Yes | Full physical address of the office |
| `email` | String | Yes | Official email address |
| `contact_number` | String | Yes | Main contact telephone number |
| `office_hours` | String | No | Office operating hours (e.g., 8:00 AM - 5:00 PM) |
| `verification_status` | String | No | Verification status ("Authenticated", "Pending", "Unverified") |
| `linked_users` | Number | No | Count of registered users linked to the office |
| `pending_requests` | Number | No | Count of pending administrative requests |
| `active_programs` | Number | No | Count of active environmental programs |
| `status` | String | No | Office status ("Active", "Inactive", "Maintenance") |
| `created_at` | Timestamp | Auto | Document creation timestamp |
| `updated_at` | Timestamp | Auto | Last update timestamp |

## Relationships

- **One-to-Many**: A company can have multiple employees
  - Reference: `employees.municipality` = `companies.municipality`
  
- **One-to-Many**: A company can have multiple departments
  - Reference: `departments.municipality` = `companies.municipality`

## Query Examples

### Get company by municipality
```javascript
const companiesRef = collection(db, 'companies');
const q = query(companiesRef, where('municipality', '==', 'San Juan'));
const snapshot = await getDocs(q);
```

### Get all active companies
```javascript
const companiesRef = collection(db, 'companies');
const q = query(companiesRef, where('status', '==', 'Active'));
const snapshot = await getDocs(q);
```

### Update company information
```javascript
const companyRef = doc(db, 'companies', companyId);
await updateDoc(companyRef, {
  email: 'newemail@denr.gov.ph',
  contact_number: '(+63) 43-555-0000',
  updated_at: new Date()
});
```

## Security Rules

```javascript
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    match /companies/{document=**} {
      // Read: Allow authenticated users
      allow read: if request.auth != null;
      
      // Write: Only allow administrators
      allow write: if request.auth != null && 
                      request.auth.token.role == 'admin';
      
      // Update: Allow municipalities to update their own office info
      allow update: if request.auth != null && 
                       request.auth.token.municipality == resource.data.municipality;
    }
  }
}
```

## Firestore Indexes

For optimal query performance, create the following indexes:

1. **Municipality + Status**: `(municipality, status)`
2. **Region + Status**: `(region, status)`
3. **Status**: Single field index for `status`

## Integration Points

### Pages Using This Collection
- `templates/municipal/hrm/company-municipal.html` - Main company information management

### Related Collections
- `employees` - Employees linked to company municipality
- `departments` - Departments within the company
- `designations` - Designations available in the company

### Data Sync Notes
- Company information is synchronized with National DENR Central Ledger
- Discrepancies must be reported to the Regional ICT unit
- Updates to company info automatically propagate to related entities

## Sample Data Initialization

See `migrate_companies.py` for script to populate initial company records.

```bash
python migrate_companies.py
```

## Audit Trail

All updates to company documents should include `updated_at` timestamp for audit purposes. Consider implementing a logs subcollection for full audit trail of changes.

# Regional System Logs - How It Works

## Overview
The **Regional System Logs** display shows all login/logout events for municipal admins under a regional admin's jurisdiction.

## How Login/Logout Events Are Captured

When a **municipal admin** logs in or logs out:

1. **Login Event** - When a municipal admin authenticates successfully via Firebase:
   - Route: `/api/set-session` (POST)
   - Code: `routes/api_routes.py` line 479-492
   - Logs to: `regional_system_logs` collection in Firestore
   - Fields captured:
     - `region`: The municipal admin's region (e.g., "REGION-IV-B")
     - `municipality`: The municipal admin's municipality (e.g., "Victoria")
     - `user`: The admin's email address
     - `action`: "LOGIN"
     - `timestamp`: When login occurred
     - `ip_address`: Client IP
     - `device_type`: Device type (Windows, MacOS, Linux, etc.)
     - `role`: "municipal_admin"

2. **Logout Event** - When a municipal admin logs out:
   - Route: `/api/logout` (POST)
   - Code: `routes/api_routes.py` line 533-545
   - Logs to: `regional_system_logs` collection
   - Same fields as login, but with `action: "LOGOUT"`

## What Regional Admins See

When a **regional admin** views `/regional/system-logs`:
- The page calls `/regional/api/system-logs` (GET)
- API returns all LOGIN/LOGOUT events for municipal admins in their region
- Events are filtered by:
  - Regional admin's region (automatically)
  - Municipalities within that region (automatically mapped)
- No login events = "No Logs Found" message

## Testing the System

### Prerequisites
1. At least one **municipal admin** account must exist
2. That admin must be assigned to a municipality within the regional admin's region
3. Examples:
   - **Municipal Admin**: `victoria.admin@denr.gov.ph` (role: "municipal_admin", municipality: "Victoria", region: "REGION-IV-B")
   - **Regional Admin**: `regional.admin@denr.gov.ph` (role: "regional_admin", region: "REGION-IV-B")

### To Test Login Capture:

1. **Create/verify municipal admin account** exists with correct region/municipality
2. **Log in as the municipal admin**:
   - Go to login page
   - Enter municipal admin credentials
   - Successfully authenticate via Firebase
   - This triggers `add_regional_system_log(..., action='LOGIN')` automatically
3. **Switch to regional admin account**:
   - Log out
   - Log in as the regional admin for that region
4. **View Regional System Logs**:
   - Navigate to `/regional/system-logs`
   - The LOGIN event from step 2 should now appear in the table
5. **Log out as municipal admin** (optional):
   - Log in again as municipal admin
   - Then log out
   - This triggers `add_regional_system_log(..., action='LOGOUT')` automatically
6. **Refresh as regional admin**:
   - The LOGOUT event should now appear in the logs

## Automatic Event Capture Code

### Login Capture (`routes/api_routes.py` line 479-492):
```python
if user_role in {'municipal', 'municipal_admin'}:
    system_logs_storage.add_regional_system_log(
        region=region,
        municipality=municipality,
        user=user_email,
        user_id=user_id,
        role=user_role,
        action='LOGIN',
        target='Authentication',
        target_id=user_id,
        module='AUTH',
        outcome='SUCCESS',
        message=f'Municipal admin {user_email} logged in.',
        ip_address=request_ip,
        device_type=device_type,
        user_agent=user_agent,
        metadata={'source': 'set-session'}
    )
```

### Logout Capture (`routes/api_routes.py` line 533-545):
```python
if user_role in {'municipal', 'municipal_admin'}:
    system_logs_storage.add_regional_system_log(
        region=region,
        municipality=municipality,
        user=user_email,
        user_id=user_id,
        role=user_role,
        action='LOGOUT',
        target='Authentication',
        target_id=user_id,
        module='AUTH',
        outcome='SUCCESS',
        message=f'Municipal admin {user_email} logged out.',
        ip_address=request_ip,
        device_type=device_type,
        user_agent=user_agent,
        metadata={'source': 'logout'}
    )
```

## Troubleshooting

### No Logs Appear
1. **Check municipal admin credentials**: Verify the user has:
   - `role: "municipal_admin"` or `role: "municipal"`
   - `municipality` field populated
   - `region` or `regionName` field populated
2. **Check regional admin credentials**: Verify the regional admin has:
   - `role: "regional_admin"` or `role: "regional"`
   - `region` or `regionName` field that matches municipal admins
3. **Check Firestore**: 
   - Query `regional_system_logs` collection directly
   - Filter by region to see if events are being stored

### Region Name Mismatch
The system automatically handles region name conversions:
- MIMAROPA ↔ REGION-IV-B
- CALABARZON ↔ REGION-IV-A
- etc.

If logs still don don't appear, check terminal output for:
```
[DEBUG] Regional system logs -> region={region}, municipalities={count}, scoped_users={count}, returned={count}
```
- If `region=unknown`, municipal admin's region is not configured
- If `returned=0`, no events match the filter criteria

### Events Being Logged to Wrong Collection
Login/logout events go to **`regional_system_logs` collection only**, not to `system_logs` collection. This is by design - only municipal admin auth events are regional-visible.

## Retention Policy
- Regional system logs are retained for **180 days**
- Automatic cleanup runs occasionally (see `REGIONAL_SYSTEM_LOGS_CLEANUP_SAMPLE_RATE` in `system_logs_storage.py`)
- Manual cleanup available via `/regional/api/system-logs/cleanup` endpoint


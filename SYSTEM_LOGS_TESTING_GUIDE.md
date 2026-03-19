# Regional System Logs - Complete Setup & Testing Guide

## What Was Fixed

1. ✅ **Enhanced logging** - Login/logout events now capture:
   - IP address of the municipal admin
   - Device type (Windows, MacOS, Linux, Mobile, etc.)
   - User email
   - Region and municipality
   - Timestamp

2. ✅ **UI improvements** - Regional system logs now display:
   - IP address with device type for each login/logout event
   - Searchable fields for IP and device type
   - Properly formatted timestamp and user information

3. ✅ **Automatic capture** - When a municipal admin logs in or out:
   - System automatically logs the event to `regional_system_logs` Firestore collection
   - Regional admin can immediately view it in `/regional/system-logs`

## How It Works

### Login Event Capture Flow

```
Municipal Admin logs in
    ↓
Frontend calls /api/set-session (POST) with Firebase credentials
    ↓
Backend route (routes/api_routes.py) processes login:
    - Resolves user's municipality from Firestore 'users' collection
    - Resolves user's region from Firestore 'users' collection
    - Extracts device type from User-Agent header
    - Extracts IP address from request headers
    ↓
If user_role is 'municipal_admin' or 'municipal':
    - Calls system_logs_storage.add_regional_system_log()
    ↓
Event stored in Firestore 'regional_system_logs' collection:
    {
      "action": "LOGIN",
      "actorEmail": "victoria.admin@denr.gov.ph",
      "municipality": "Victoria",
      "region": "REGION-IV-B",
      "ip": "192.168.1.100",
      "device_type": "Windows",
      "timestamp": "2026-03-19T10:30:45.123456",
      ...
    }
    ↓
Regional Admin views /regional/system-logs
    ↓
Frontend calls /regional/api/system-logs (GET)
    ↓
Backend API:
    - Resolves regional admin's region
    - Queries 'regional_system_logs' collection by region
    - Returns matching events with IP and device type
    ↓
UI displays table with:
    | Timestamp | User | Region/Municipality | Action | Details | IP (Device) |
    | 10:30 AM  | victoria.admin@... | REGION-IV-B (Victoria) | LOGIN | ... | 192.168.1.100 (Windows) |
```

### Logout Event Capture Flow
Same as login, but:
- Route: `/api/logout` (POST)
- Action recorded: "LOGOUT"
- Triggered when user clicks logout or session expires

## Prerequisites for Testing

### Step 1: Verify Municipal Admin Exists
A municipal admin account must exist in Firestore `users` collection with:
```json
{
  "email": "victoria.admin@denr.gov.ph",
  "role": "municipal_admin",
  "municipality": "Victoria",
  "region": "REGION-IV-B",
  "regionName": "MIMAROPA"  // or other region formats
}
```

### Step 2: Verify Regional Admin Exists
A regional admin account must exist with same region:
```json
{
  "email": "regional.admin@denr.gov.ph",
  "role": "regional_admin",
  "region": "REGION-IV-B",
  "regionName": "MIMAROPA"
}
```

### Step 3: Restart Flask Server
To apply the logging changes:
```bash
# Kill existing Flask process
# Then restart:
python app.py
```

## Testing the System

### Test Case 1: Capture Login Event

1. **Open terminal** and monitor Flask logs:
   ```
   [LOGIN_CAPTURE] Recording login event for victoria.admin@denr.gov.ph...
   [LOGIN_CAPTURE] ✅ Login event recorded successfully for victoria.admin@...
   ```

2. **Log in as municipal admin**:
   - Go to `/login`
   - Enter Victoria municipal admin credentials
   - Click Login
   - Check terminal - should see `[LOGIN_CAPTURE]` lines

3. **Switch to regional admin**:
   - Log out
   - Log in with regional admin credentials
   - Navigate to `/regional/system-logs`

4. **Verify login event appears**:
   - You should see a row with:
     - Action: "LOGIN"
     - User: "victoria.admin@denr.gov.ph"
     - IP: "127.0.0.1" or actual client IP
     - Device: "(Windows)" or whatever device was used

### Test Case 2: Capture Logout Event

1. **While logged in as municipal admin**:
   - Click Logout button
   - Check Flask terminal - should see `[LOGOUT_CAPTURE]` lines

2. **Switch to regional admin**:
   - Go to `/regional/system-logs`
   - Refresh page
   - Should see LOGOUT event below the LOGIN event

### Test Case 3: Verify Filtering Works

1. **With multiple login/logout events**:
   - Use the **Search** field: type "Windows" or an IP address
   - Use the **Action** filter: select "LOGIN" or "LOGOUT"
   - Use the **User** filter: select specific admin email
   - UI should re-filter in real-time

### Test Case 4: Verify Device Type Capture

1. **Log in from different devices** (if available):
   - Windows PC
   - Mac
   - Mobile device (iPhone, Android)
   - Each login should show different device type

2. **Verify device type displays** in the IP column:
   ```
   192.168.1.100
   (Windows)
   ```

## Troubleshooting

### Issue: No login events appear

**Diagnostic 1: Check terminal for capture logs**
```
Look for: [LOGIN_CAPTURE] Recording login event...
         [LOGIN_CAPTURE] ✅ Login event recorded successfully
```

If missing:
- User may not be a municipal admin (check `role` field in Firestore)
- Flask may not have restarted (restart Flask server)

**Diagnostic 2: Check Firestore collection directly**
```
Firestore → regional_system_logs collection
Filter by: region == "REGION-IV-B"
          action == "LOGIN"
```

If no records exist:
- No login events have been captured yet (log in as municipal admin first)
- Region name may not match (check Get `get_user_region()` output in terminal)

**Diagnostic 3: Check regional admin's region**
```
Firestore → users collection
Search for regional admin email
Check: region, regionName fields match municipal admins
```

### Issue: IP address shows as empty

**Cause**: Request IP extraction failed
**Solution**: The system falls back to showing just device type, which is still useful

### Issue: Device type shows as "Unknown"

**Cause**: User-Agent header not recognized
**Solution**: Device type will still be captured for common browsers; this is normal

### Issue: Events from other municipalities appear

**This should NOT happen** - API filters by regional admin's region scope automatically. If it does:
- Check terminal output: `[DEBUG] Regional system logs -> region=...`
- Verify `municipality_set` is not empty
- Check Firestore index on `regional_system_logs` collection (region, created_at)

## Code Changes Summary

### routes/api_routes.py
- **Line 479-500**: Added `[LOGIN_CAPTURE]` debug logging
- **Line 533-551**: Added `[LOGOUT_CAPTURE]` debug logging

### routes/regional_routes.py
- **Line 625-643**: Updated to extract and preserve IP address and device type from regional_system_logs

### templates/regional/logs/system-logs.html
- **Line 279-280**: Added device_type variable extraction
- **Line 282**: Added device to searchBlob for filter matching
- **Line 318-320**: Updated UI to display device type below IP address

## Database Schema

Events stored in Firestore `regional_system_logs` collection:
```
{
  "id": "auto-generated-doc-id",
  "action": "LOGIN" | "LOGOUT",
  "actorEmail": "victoria.admin@denr.gov.ph",
  "actorId": "user_victoria_admin",
  "actorRole": "municipal_admin",
  "created_at": Timestamp (server),
  "device_type": "Windows" | "MacOS" | "Linux" | "Mobile" | "Unknown",
  "expires_at": Timestamp (now + 180 days),
  "ip": "192.168.1.100",
  "ipAddress": "192.168.1.100",
  "message": "Municipal admin victoria.admin@denr.gov.ph logged in.",
  "metadata": { "source": "set-session" },
  "module": "AUTH",
  "municipality": "Victoria",
  "outcome": "SUCCESS",
  "region": "REGION-IV-B",
  "role": "municipal_admin",
  "scope": "MUNICIPAL",
  "target": "Authentication",
  "targetId": "user_victoria_admin",
  "timestamp": "2026-03-19T10:30:45.123456",
  "user": "victoria.admin@denr.gov.ph",
  "user_agent": "Mozilla/5.0...",
  "user_id": "user_victoria_admin"
}
```

## Performance Notes

- Regional system logs are **retained for 180 days** (configurable via `REGIONAL_SYSTEM_LOGS_RETENTION_DAYS`)
- Automatic cleanup runs occasionally to delete expired entries
- Max 40 most recent logs displayed per regional admin (configurable at line 834 in regional_routes.py)
- Query uses index on (region, created_at) for fast filtering

## Next Steps

1. ✅ Restart Flask server
2. ✅ Log in as municipal admin (watch terminal for `[LOGIN_CAPTURE]`)
3. ✅ Switch to regional admin account
4. ✅ View `/regional/system-logs` 
5. ✅ Verify login event appears with IP and device type
6. ✅ Log out as municipal admin (watch for `[LOGOUT_CAPTURE]`)
7. ✅ Refresh regional logs - verify logout event appears


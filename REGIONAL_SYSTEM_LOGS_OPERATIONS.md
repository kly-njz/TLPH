# Regional System Logs Operations

This document describes index and retention setup for the `regional_system_logs` collection.

## What Is Already Implemented In Code

- Every new regional system log writes:
  - `created_at` (server timestamp)
  - `expires_at` (default: 180 days from write time)
- The app performs a lightweight best-effort cleanup of expired rows during writes.
- Regional log reads use a region-scoped query path first, then safe fallback.

## Recommended Firestore Index

Create a composite index for fast region-scoped newest-first reads:

- Collection: `regional_system_logs`
- Fields:
  - `region` Ascending
  - `created_at` Descending

This supports queries like:

- `where(region == <region>).order_by(created_at desc).limit(n)`

## Recommended Firestore TTL

Enable Firestore TTL to auto-delete old rows:

- Collection: `regional_system_logs`
- TTL field: `expires_at`

Notes:

- Keep the app-level cleanup enabled as a safety net.
- TTL deletion is asynchronous and may not remove docs immediately at the exact expiration time.

## Tune Retention Window

Update these constants in `system_logs_storage.py` if needed:

- `REGIONAL_SYSTEM_LOGS_RETENTION_DAYS`
- `REGIONAL_SYSTEM_LOGS_CLEANUP_SAMPLE_RATE`
- `REGIONAL_SYSTEM_LOGS_CLEANUP_BATCH`

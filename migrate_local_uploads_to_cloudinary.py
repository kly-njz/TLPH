import os
import re
import time
import json
import hashlib
import argparse
from typing import Any, Dict, List, Tuple

import requests
from dotenv import load_dotenv
import firebase_admin
from firebase_admin import credentials, firestore


LOCAL_UPLOAD_PREFIXES = (
    '/static/uploads/',
    'static/uploads/',
)

DEFAULT_COLLECTIONS = [
    'users',
    'applications',
    'service_requests',
    'inventory_registrations',
    'license_applications',
]


def init_firestore(creds_path: str):
    if not firebase_admin._apps:
        cred = credentials.Certificate(creds_path)
        firebase_admin.initialize_app(cred)
    return firestore.client()


def cloudinary_signature(params: Dict[str, Any], api_secret: str) -> str:
    filtered = {k: v for k, v in params.items() if v is not None and v != ''}
    base = '&'.join(f"{k}={filtered[k]}" for k in sorted(filtered.keys()))
    return hashlib.sha1(f"{base}{api_secret}".encode('utf-8')).hexdigest()


def upload_file_to_cloudinary(file_path: str, folder: str, cloud_name: str, api_key: str, api_secret: str) -> str:
    timestamp = int(time.time())
    sign_params = {
        'folder': folder,
        'timestamp': timestamp,
    }
    signature = cloudinary_signature(sign_params, api_secret)

    endpoint = f"https://api.cloudinary.com/v1_1/{cloud_name}/auto/upload"
    filename = os.path.basename(file_path)

    with open(file_path, 'rb') as f:
        resp = requests.post(
            endpoint,
            data={
                'api_key': api_key,
                'timestamp': timestamp,
                'folder': folder,
                'signature': signature,
            },
            files={
                'file': (filename, f, 'application/octet-stream')
            },
            timeout=90,
        )

    if not resp.ok:
        raise RuntimeError(f"Cloudinary error {resp.status_code}: {resp.text[:400]}")

    payload = resp.json() or {}
    out = payload.get('secure_url') or payload.get('url')
    if not out:
        raise RuntimeError(f"Cloudinary did not return URL for {file_path}")
    return out


def is_local_upload_url(value: str) -> bool:
    if not isinstance(value, str):
        return False
    v = value.strip()
    return any(v.startswith(prefix) for prefix in LOCAL_UPLOAD_PREFIXES)


def local_url_to_disk_path(url: str, project_root: str) -> str:
    v = url.strip()
    v = re.sub(r'^https?://[^/]+', '', v, flags=re.IGNORECASE)
    if v.startswith('/'):
        v = v[1:]
    # at this point should be static/uploads/...
    return os.path.join(project_root, v.replace('/', os.sep))


def migrate_value(
    value: Any,
    *,
    project_root: str,
    cloud_name: str,
    api_key: str,
    api_secret: str,
    cloud_folder_prefix: str,
    uploaded_cache: Dict[str, str],
    stats: Dict[str, int],
    errors: List[str],
) -> Tuple[Any, bool]:
    changed = False

    if isinstance(value, dict):
        out = {}
        for k, v in value.items():
            new_v, did_change = migrate_value(
                v,
                project_root=project_root,
                cloud_name=cloud_name,
                api_key=api_key,
                api_secret=api_secret,
                cloud_folder_prefix=cloud_folder_prefix,
                uploaded_cache=uploaded_cache,
                stats=stats,
                errors=errors,
            )
            out[k] = new_v
            changed = changed or did_change
        return out, changed

    if isinstance(value, list):
        out_list = []
        for item in value:
            new_item, did_change = migrate_value(
                item,
                project_root=project_root,
                cloud_name=cloud_name,
                api_key=api_key,
                api_secret=api_secret,
                cloud_folder_prefix=cloud_folder_prefix,
                uploaded_cache=uploaded_cache,
                stats=stats,
                errors=errors,
            )
            out_list.append(new_item)
            changed = changed or did_change
        return out_list, changed

    if isinstance(value, str) and is_local_upload_url(value):
        disk_path = local_url_to_disk_path(value, project_root)
        if not os.path.exists(disk_path):
            stats['missing_files'] += 1
            errors.append(f"Missing local file for URL '{value}' -> '{disk_path}'")
            return value, False

        if disk_path in uploaded_cache:
            return uploaded_cache[disk_path], True

        try:
            # Keep folder structure in Cloudinary for easier tracing
            rel = os.path.relpath(disk_path, project_root).replace('\\', '/')
            # e.g. static/uploads/service_requests/uid/file.pdf -> tlph/migrated/service_requests/uid
            parts = rel.split('/')
            cloud_folder = cloud_folder_prefix
            if len(parts) >= 4 and parts[0] == 'static' and parts[1] == 'uploads':
                cloud_folder = f"{cloud_folder_prefix}/{parts[2]}"
                if len(parts) >= 5:
                    cloud_folder = f"{cloud_folder}/{parts[3]}"

            cloud_url = upload_file_to_cloudinary(
                disk_path,
                cloud_folder,
                cloud_name,
                api_key,
                api_secret,
            )
            uploaded_cache[disk_path] = cloud_url
            stats['uploaded_files'] += 1
            return cloud_url, True
        except Exception as exc:
            stats['upload_errors'] += 1
            errors.append(f"Upload failed '{disk_path}': {exc}")
            return value, False

    return value, False


def migrate_collection(
    db,
    collection_name: str,
    *,
    apply_updates: bool,
    project_root: str,
    cloud_name: str,
    api_key: str,
    api_secret: str,
    cloud_folder_prefix: str,
    uploaded_cache: Dict[str, str],
    stats: Dict[str, int],
    errors: List[str],
):
    docs = list(db.collection(collection_name).stream())
    stats['docs_scanned'] += len(docs)

    for d in docs:
        data = d.to_dict() or {}
        new_data, changed = migrate_value(
            data,
            project_root=project_root,
            cloud_name=cloud_name,
            api_key=api_key,
            api_secret=api_secret,
            cloud_folder_prefix=cloud_folder_prefix,
            uploaded_cache=uploaded_cache,
            stats=stats,
            errors=errors,
        )

        if changed:
            stats['docs_changed'] += 1
            if apply_updates:
                db.collection(collection_name).document(d.id).set(new_data, merge=False)
                stats['docs_updated'] += 1


def main():
    load_dotenv()

    parser = argparse.ArgumentParser(description='Migrate local /static/uploads URLs in Firestore docs to Cloudinary URLs')
    parser.add_argument('--project-root', default='.', help='Path to project root (default: current directory)')
    parser.add_argument('--credentials', default=os.environ.get('FIREBASE_CREDENTIALS', 'firebase-credentials.json'), help='Firebase service account JSON path')
    parser.add_argument('--collections', default=','.join(DEFAULT_COLLECTIONS), help='Comma-separated Firestore collections to scan')
    parser.add_argument('--cloud-folder-prefix', default='tlph/migrated', help='Cloudinary folder prefix')
    parser.add_argument('--apply', action='store_true', help='Apply updates to Firestore. If omitted, dry-run only.')
    parser.add_argument('--report', default='migration_cloudinary_report.json', help='Path to write migration report JSON')

    args = parser.parse_args()

    project_root = os.path.abspath(args.project_root)
    credentials_path = args.credentials

    cloud_name = os.environ.get('CLOUDINARY_CLOUD_NAME', '').strip()
    api_key = os.environ.get('CLOUDINARY_API_KEY', '').strip()
    api_secret = os.environ.get('CLOUDINARY_API_SECRET', '').strip()

    if not cloud_name or not api_key or not api_secret:
        raise SystemExit('Missing Cloudinary env vars: CLOUDINARY_CLOUD_NAME, CLOUDINARY_API_KEY, CLOUDINARY_API_SECRET')

    if not os.path.exists(credentials_path):
        raise SystemExit(f'Firebase credentials not found: {credentials_path}')

    collections = [c.strip() for c in args.collections.split(',') if c.strip()]
    if not collections:
        raise SystemExit('No collections provided')

    db = init_firestore(credentials_path)

    stats = {
        'docs_scanned': 0,
        'docs_changed': 0,
        'docs_updated': 0,
        'uploaded_files': 0,
        'missing_files': 0,
        'upload_errors': 0,
    }
    errors: List[str] = []
    uploaded_cache: Dict[str, str] = {}

    for collection_name in collections:
        print(f"[INFO] Scanning collection: {collection_name}")
        migrate_collection(
            db,
            collection_name,
            apply_updates=args.apply,
            project_root=project_root,
            cloud_name=cloud_name,
            api_key=api_key,
            api_secret=api_secret,
            cloud_folder_prefix=args.cloud_folder_prefix,
            uploaded_cache=uploaded_cache,
            stats=stats,
            errors=errors,
        )

    report = {
        'apply_mode': args.apply,
        'project_root': project_root,
        'collections': collections,
        'stats': stats,
        'errors': errors,
        'timestamp': int(time.time()),
    }

    with open(args.report, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print('\n=== Migration Summary ===')
    print(json.dumps(stats, indent=2))
    print(f"Report written to: {os.path.abspath(args.report)}")
    if errors:
        print(f"Warnings/Errors: {len(errors)} (see report)")


if __name__ == '__main__':
    main()

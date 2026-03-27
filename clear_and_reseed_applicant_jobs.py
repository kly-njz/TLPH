"""Clear and reseed municipal_denr_applicant_jobs with canonical applicant fields.

Canonical fields:
- full_name
- candidate_type
- region_office
- status (APPROVED | REJECTED | PENDING)
"""

import firebase_admin
from firebase_admin import credentials, firestore


def _normalize_status(raw: str) -> str:
    value = str(raw or "").strip().upper()
    if value in {"APPROVED", "REJECTED", "PENDING"}:
        return value
    return "PENDING"


def _safe_text(value, default="N/A") -> str:
    text = str(value or "").strip()
    return text if text else default


def main() -> None:
    if not firebase_admin._apps:
        cred = credentials.Certificate("firebase-credentials.json")
        firebase_admin.initialize_app(cred)

    db = firestore.client()

    print("[INFO] Clearing municipal_denr_applicant_jobs...")
    jobs_docs = list(db.collection("municipal_denr_applicant_jobs").stream())
    for doc in jobs_docs:
        doc.reference.delete()
    print(f"[INFO] Deleted {len(jobs_docs)} job documents")

    print("[INFO] Reseeding from applications collection...")
    source_docs = list(db.collection("applications").stream())
    seeded = 0

    for source_doc in source_docs:
        src = source_doc.to_dict() or {}

        full_name = _safe_text(
            src.get("full_name")
            or src.get("applicant_name")
            or src.get("applicantName")
            or src.get("fullName")
            or src.get("name")
            or src.get("userName")
        )
        candidate_type = _safe_text(
            src.get("candidate_type")
            or src.get("category")
            or src.get("application_type")
            or src.get("applicantCategory")
            or "DENR Application"
        )
        region_office = _safe_text(
            src.get("region_office")
            or src.get("region")
            or src.get("region_name")
            or src.get("regionName")
            or src.get("target_region")
        )
        municipality = _safe_text(
            src.get("municipality")
            or src.get("municipality_name")
            or src.get("municipalityName")
            or src.get("target_municipality")
        )

        status = _normalize_status(src.get("status") or src.get("employeeStatus"))

        reference_id = _safe_text(
            src.get("reference_id")
            or src.get("referenceId")
            or src.get("ref_code")
            or source_doc.id[:8].upper(),
            default=source_doc.id[:8].upper(),
        )
        if reference_id.upper().startswith("APP-"):
            reference_id = reference_id[4:]

        def norm_key(v: str) -> str:
            return " ".join(str(v or "").strip().upper().split())

        payload = {
            "source_id": source_doc.id,
            "source_collection": "applications",
            "full_name": full_name,
            "candidate_type": candidate_type,
            "region_office": region_office,
            "status": status,
            "employeeStatus": status.lower(),
            # Backward-compatible fields
            "applicant_name": full_name,
            "category": candidate_type,
            "region": region_office,
            "municipality": municipality,
            "municipality_key": norm_key(municipality),
            "region_key": norm_key(region_office),
            "reference_id": reference_id,
            "created_at": src.get("created_at") or src.get("submittedAt") or firestore.SERVER_TIMESTAMP,
            "updated_at": firestore.SERVER_TIMESTAMP,
            "date_filed": _safe_text(src.get("date_filed"), default=""),
            "job_title": f"{candidate_type} Review",
            "job_description": "Validate DENR applicant records for regional and municipal processing.",
        }

        db.collection("municipal_denr_applicant_jobs").document(f"APP-{source_doc.id}").set(payload, merge=True)
        seeded += 1

    print(f"[INFO] Seeded {seeded} documents into municipal_denr_applicant_jobs")
    print("[DONE] Applicant jobs collection reset complete")


if __name__ == "__main__":
    main()

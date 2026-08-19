import os
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
from dotenv import load_dotenv

# Load environment variables with override
load_dotenv(override=True)

logger = logging.getLogger(__name__)


# Cache the supabase client instance
_supabase_client = None


def is_database_configured() -> bool:
    """Check whether Supabase environment variables are present."""
    url = os.getenv("SUPABASE_URL", "").strip()
    key = os.getenv("SUPABASE_KEY", "").strip()
    return bool(url and key)


def check_database_status() -> Dict[str, Any]:
    """Check connection status and whether the required tables exist in Supabase."""
    if not is_database_configured():
        return {
            "status": "unconfigured",
            "message": "Supabase credentials not configured in .env"
        }

    client = get_supabase_client()
    if not client:
        return {
            "status": "client_error",
            "message": "Failed to initialize Supabase client"
        }

    try:
        client.table("patients").select("id").limit(1).execute()
        return {
            "status": "connected",
            "message": "Supabase connected and PostgreSQL tables verified active."
        }
    except Exception as e:
        err_str = str(e)
        if "42501" in err_str or "row-level security" in err_str.lower():
            return {
                "status": "rls_blocked",
                "message": "Supabase connected, but Row-Level Security (RLS) is blocking data writes. Run the RLS disable command in Supabase SQL editor."
            }
        if "PGRST205" in err_str or "schema cache" in err_str or "Could not find the table" in err_str:
            return {
                "status": "tables_missing",
                "message": "Connected to Supabase, but tables have not been created in PostgreSQL yet. Run supabase_schema.sql in the Supabase SQL Editor."
            }
        return {
            "status": "error",
            "message": f"Database connection warning: {err_str}"
        }




def get_supabase_client():
    """
    Initialize and return the Supabase client instance.
    Returns None if credentials are not configured or client creation fails.
    """
    global _supabase_client
    if _supabase_client is not None:
        return _supabase_client

    url = os.getenv("SUPABASE_URL", "").strip()
    key = os.getenv("SUPABASE_KEY", "").strip()

    if not url or not key:
        logger.warning("Supabase URL or Key not set. Persistence will be skipped.")
        return None

    try:
        from supabase import create_client
        _supabase_client = create_client(url, key)
        return _supabase_client
    except Exception as e:
        logger.error(f"Failed to initialize Supabase client: {e}")
        return None


def save_patient(patient_data: Dict[str, Any]) -> Optional[str]:
    """
    Insert structured patient record into the 'patients' table.
    Returns the generated UUID record ID on success, or None on failure.
    """
    import uuid
    client = get_supabase_client()
    if client is None:
        return None

    try:
        inserted_id = str(uuid.uuid4())
        # Prepare data adhering to table schema
        payload = {
            "id": inserted_id,
            "patient_id": patient_data.get("patient_id"),
            "patient_name": patient_data.get("patient_name"),
            "age": patient_data.get("age") if isinstance(patient_data.get("age"), int) else (
                int(float(patient_data.get("age"))) if patient_data.get("age") is not None and str(patient_data.get("age")).isdigit() else None
            ),
            "gender": patient_data.get("gender"),
            "payer": patient_data.get("payer"),
            "diagnosis": patient_data.get("diagnosis"),
            "icd10_code": patient_data.get("icd10_code"),
            "severity": patient_data.get("severity"),
            "severity_evidence": patient_data.get("severity_evidence") or [],
            "previous_treatment": patient_data.get("previous_treatment") or [],
            "previous_procedure": patient_data.get("previous_procedure") or [],
            "requested_service": patient_data.get("requested_service"),
            "cpt_hcpcs_code": patient_data.get("cpt_hcpcs_code"),
            "quantity": str(patient_data.get("quantity")) if patient_data.get("quantity") is not None else None,
            "frequency": str(patient_data.get("frequency")) if patient_data.get("frequency") is not None else None,
            "provider_specialty": patient_data.get("provider_specialty"),
            "facility_type": patient_data.get("facility_type"),
            "documentation": patient_data.get("documentation") or {},
            "clinical_information": patient_data.get("clinical_information") or {},
        }

        response = client.table("patients").insert(payload).execute()
        if response.data and len(response.data) > 0:
            rec_id = response.data[0].get("id") or inserted_id
            logger.info(f"Patient saved successfully with ID: {rec_id}")
            return rec_id
        return inserted_id
    except Exception as e:
        logger.error(f"Error saving patient to Supabase: {e}")
        return None


def create_authorization_request_record(
    patient_record_id: Optional[str],
    patient_data: Dict[str, Any],
    status: str = "PENDING"
) -> Dict[str, Any]:
    """
    Insert a prior authorization request into 'authorization_requests'.
    Returns dictionary containing 'id' and 'created_at'.
    """
    import uuid
    client = get_supabase_client()
    default_id = str(uuid.uuid4())
    default_ts = datetime.utcnow().isoformat()

    if client is None:
        return {"id": default_id, "created_at": default_ts}

    try:
        payload = {
            "id": default_id,
            "patient_id": patient_record_id,
            "requested_service": patient_data.get("requested_service"),
            "cpt_hcpcs_code": patient_data.get("cpt_hcpcs_code"),
            "quantity": str(patient_data.get("quantity")) if patient_data.get("quantity") is not None else None,
            "frequency": str(patient_data.get("frequency")) if patient_data.get("frequency") is not None else None,
            "payer": patient_data.get("payer"),
            "request_status": status,
        }

        response = client.table("authorization_requests").insert(payload).execute()
        if response.data and len(response.data) > 0:
            rec = response.data[0]
            req_id = rec.get("id") or default_id
            req_ts = rec.get("created_at") or default_ts
            logger.info(f"Authorization request created with ID: {req_id}")
            return {"id": req_id, "created_at": req_ts}
        return {"id": default_id, "created_at": default_ts}
    except Exception as e:
        logger.error(f"Error creating authorization request in Supabase: {e}")
        return {"id": default_id, "created_at": default_ts}


def create_authorization_request(
    patient_record_id: Optional[str],
    patient_data: Dict[str, Any],
    status: str = "PENDING"
) -> Optional[str]:
    """
    Insert a prior authorization request into 'authorization_requests'.
    Returns the created request UUID on success, or a valid UUID string fallback.
    """
    rec = create_authorization_request_record(patient_record_id, patient_data, status)
    return rec.get("id")


def save_prediction(
    request_id: Optional[str],
    prediction_data: Dict[str, Any]
) -> Optional[str]:
    """
    Insert ML prediction signal into the 'predictions' table.
    Returns the created prediction record ID on success, or None on failure.
    """
    client = get_supabase_client()
    if client is None:
        return None

    try:
        payload = {
            "request_id": request_id,
            "model_name": prediction_data.get("model_name", "Random Forest"),
            "model_version": prediction_data.get("model_version", "1.0"),
            "predicted_class": prediction_data.get("predicted_class"),
            "approval_probability": prediction_data.get("approval_probability"),
            "denial_probability": prediction_data.get("denial_probability"),
            "review_probability": prediction_data.get("review_probability"),
        }

        response = client.table("predictions").insert(payload).execute()
        if response.data and len(response.data) > 0:
            pred_id = response.data[0].get("id")
            logger.info(f"Prediction saved with ID: {pred_id}")
            return pred_id
        return None
    except Exception as e:
        logger.error(f"Error saving prediction to Supabase: {e}")
        return None


def save_decision(
    request_id: Optional[str],
    decision_result: Dict[str, Any]
) -> Optional[str]:
    """
    Insert final deterministic decision into the 'decisions' table.
    Returns the decision record ID on success, or None on failure.
    """
    import uuid
    client = get_supabase_client()
    if client is None:
        return None

    try:
        dec_id = str(uuid.uuid4())
        payload = {
            "id": dec_id,
            "request_id": request_id,
            "policy_id": decision_result.get("policy_id") or decision_result.get("applied_policy_id"),
            "policy_name": decision_result.get("policy_name") or decision_result.get("applied_policy_name"),
            "final_decision": decision_result.get("decision", "MANUAL REVIEW"),
            "failed_criteria": decision_result.get("failed_criteria") or [],
            "manual_review_reasons": decision_result.get("manual_review_reasons") or [],
        }

        response = client.table("decisions").insert(payload).execute()
        if response.data and len(response.data) > 0:
            decision_id = response.data[0].get("id") or dec_id
            logger.info(f"Decision saved with ID: {decision_id}")
            return decision_id
        return dec_id
    except Exception as e:
        logger.error(f"Error saving decision to Supabase: {e}")
        return None


def save_decision_criteria(
    decision_id: Optional[str],
    criteria_list: List[Dict[str, Any]]
) -> bool:
    """
    Insert individual rule engine criteria results into the 'decision_criteria' table.
    Returns True if successfully inserted, False otherwise.
    """
    import uuid
    if not decision_id or not criteria_list:
        return False

    client = get_supabase_client()
    if client is None:
        return False

    try:
        payloads = []
        for item in criteria_list:
            if not isinstance(item, dict):
                continue
            payloads.append({
                "id": str(uuid.uuid4()),
                "decision_id": decision_id,
                "criterion": item.get("criterion", "Unknown Criterion"),
                "status": item.get("status", "UNKNOWN"),
                "reason": item.get("reason", ""),
            })

        if not payloads:
            return True

        response = client.table("decision_criteria").insert(payloads).execute()
        logger.info(f"Saved {len(payloads)} decision criteria rows for decision {decision_id}")
        return bool(response.data)
    except Exception as e:
        logger.error(f"Error saving decision criteria to Supabase: {e}")
        return False


def update_authorization_request_status(request_id: Optional[str], status: str) -> bool:
    """
    Update request_status of an authorization request.
    """
    if not request_id:
        return False

    client = get_supabase_client()
    if client is None:
        return False

    try:
        response = client.table("authorization_requests").update({
            "request_status": status
        }).eq("id", request_id).execute()
        return bool(response.data)
    except Exception as e:
        logger.error(f"Error updating authorization request status: {e}")
        return False


def get_recent_requests(limit: int = 50) -> List[Dict[str, Any]]:
    """
    Fetch recent authorization requests with linked patient and decision data,
    strictly ordered by authorization_requests.created_at DESC.
    """
    client = get_supabase_client()
    if client is None:
        return []

    try:
        response = client.table("authorization_requests") \
            .select("*, patients(*), decisions(*)") \
            .order("created_at", desc=True) \
            .limit(limit) \
            .execute()
        data = response.data or []
        data.sort(key=lambda x: str(x.get("created_at") or ""), reverse=True)
        return data

    except Exception as e:
        logger.error(f"Error fetching recent requests: {e}")
        return []


def update_patient_clinical_data(db_patient_id: Optional[str], patient_data: Dict[str, Any]) -> bool:
    """
    Update clinical facts (diagnosis, CPT, procedures, treatments, etc.) on an existing patient record in Supabase.
    """
    if not db_patient_id:
        return False

    client = get_supabase_client()
    if client is None:
        return False

    try:
        payload = {
            "diagnosis": patient_data.get("diagnosis"),
            "icd10_code": patient_data.get("icd10_code"),
            "severity": patient_data.get("severity"),
            "severity_evidence": patient_data.get("severity_evidence") or [],
            "previous_treatment": patient_data.get("previous_treatment") or [],
            "previous_procedure": patient_data.get("previous_procedure") or [],
            "requested_service": patient_data.get("requested_service"),
            "cpt_hcpcs_code": patient_data.get("cpt_hcpcs_code"),
            "quantity": str(patient_data.get("quantity")) if patient_data.get("quantity") is not None else None,
            "frequency": str(patient_data.get("frequency")) if patient_data.get("frequency") is not None else None,
            "provider_specialty": patient_data.get("provider_specialty"),
            "facility_type": patient_data.get("facility_type"),
            "documentation": patient_data.get("documentation") or {},
            "clinical_information": patient_data.get("clinical_information") or {},
        }
        if patient_data.get("payer"):
            payload["payer"] = patient_data.get("payer")

        response = client.table("patients").update(payload).eq("id", db_patient_id).execute()
        return bool(response.data)
    except Exception as e:
        logger.error(f"Error updating patient clinical data in Supabase: {e}")
        return False


def update_authorization_request_details(request_id: Optional[str], patient_data: Dict[str, Any], status: Optional[str] = None) -> bool:
    """
    Update requested service and CPT details on an existing authorization request in Supabase.
    """
    if not request_id:
        return False

    client = get_supabase_client()
    if client is None:
        return False

    try:
        payload = {
            "requested_service": patient_data.get("requested_service"),
            "cpt_hcpcs_code": patient_data.get("cpt_hcpcs_code"),
            "quantity": str(patient_data.get("quantity")) if patient_data.get("quantity") is not None else None,
            "frequency": str(patient_data.get("frequency")) if patient_data.get("frequency") is not None else None,
            "payer": patient_data.get("payer"),
        }
        if status:
            payload["request_status"] = status

        response = client.table("authorization_requests").update(payload).eq("id", request_id).execute()
        return bool(response.data)
    except Exception as e:
        logger.error(f"Error updating authorization request details: {e}")
        return False


def get_decision_criteria(decision_id: str) -> List[Dict[str, Any]]:
    """
    Fetch all criteria rows evaluated for a specific decision.
    """
    client = get_supabase_client()
    if client is None:
        return []

    try:
        response = client.table("decision_criteria") \
            .select("*") \
            .eq("decision_id", decision_id) \
            .execute()
        return response.data or []
    except Exception as e:
        logger.error(f"Error fetching decision criteria: {e}")
        return []


def save_document_metadata(
    request_id: Optional[str],
    document_type: str,
    file_name: str,
    identity_status: str = "VERIFIED",
    pdf_bytes: Optional[bytes] = None
) -> Optional[str]:
    """
    Insert document tracking metadata into 'documents' table.
    Uploads file to Supabase Storage if configured and available.
    """
    if not request_id:
        return None

    import uuid
    client = get_supabase_client()
    doc_id = str(uuid.uuid4())
    storage_path = None

    if client is not None and pdf_bytes:
        try:
            storage_path = f"requests/{request_id}/{file_name}"
            try:
                client.storage.from_("clinical-documents").upload(
                    path=storage_path,
                    file=pdf_bytes,
                    file_options={"content-type": "application/pdf", "upsert": "true"}
                )
            except Exception as st_err:
                logger.info(f"Supabase Storage bucket upload skipped or not configured: {st_err}")
        except Exception as e:
            logger.debug(f"Storage path generation skipped: {e}")

    if client is None:
        return doc_id

    try:
        payload = {
            "id": doc_id,
            "request_id": request_id,
            "document_type": document_type,
            "file_name": file_name,
            "storage_path": storage_path,
            "identity_verification_status": identity_status,
            "processing_status": "PROCESSED"
        }
        try:
            response = client.table("documents").insert(payload).execute()
            if response.data and len(response.data) > 0:
                return response.data[0].get("id") or doc_id
        except Exception as p_err:
            min_payload = {
                "id": doc_id,
                "request_id": request_id,
                "document_type": document_type,
                "file_name": file_name,
                "storage_path": storage_path
            }
            try:
                response = client.table("documents").insert(min_payload).execute()
                if response.data and len(response.data) > 0:
                    return response.data[0].get("id") or doc_id
            except Exception as e2:
                logger.debug(f"Minimal document insert notice: {e2}")
        return doc_id
    except Exception as e:
        logger.warning(f"Note: Could not insert document metadata into Supabase (table may require schema update): {e}")
        return doc_id


def save_identity_verification(
    request_id: Optional[str],
    verification_data: Dict[str, Any]
) -> Optional[str]:
    """
    Insert local deterministic identity verification audit record into 'identity_verifications' table
    and update documents identity_verification_status column.
    """
    if not request_id or not verification_data:
        return None

    import uuid
    client = get_supabase_client()
    ver_id = str(uuid.uuid4())
    if client is None:
        return ver_id

    try:
        is_verified = bool(verification_data.get("verified"))
        identity_status = "MATCH" if is_verified else "MISMATCH"
        fields = verification_data.get("fields") or {}
        verified_fields = {k: v for k, v in fields.items() if v == "MATCH"}
        mismatch_fields = {k: v for k, v in fields.items() if v == "MISMATCH"}

        payload = {
            "id": ver_id,
            "request_id": request_id,
            "identity_status": identity_status,
            "verified_fields": verified_fields,
            "mismatch_fields": mismatch_fields
        }

        # 1. Sync identity_verification_status onto documents table
        try:
            client.table("documents").update({
                "identity_verification_status": identity_status
            }).eq("request_id", request_id).execute()
        except Exception as doc_err:
            logger.debug(f"Document identity status update notice: {doc_err}")

        # 2. Insert record into identity_verifications table
        try:
            response = client.table("identity_verifications").insert(payload).execute()
            if response.data and len(response.data) > 0:
                return response.data[0].get("id") or ver_id
            return ver_id
        except Exception as table_err:
            logger.info(f"Note: identity_verifications table insert notice: {table_err}")
            return ver_id
    except Exception as e:
        logger.warning(f"Note: Could not insert identity verification into Supabase: {e}")
        return ver_id


def save_clinical_facts(
    request_id: Optional[str],
    patient_data: Dict[str, Any],
    model_name: str = "Groq LLM"
) -> Optional[str]:
    """
    Insert extracted, normalized clinical facts into 'clinical_facts' table.
    """
    if not request_id or not patient_data:
        return None

    import uuid
    client = get_supabase_client()
    facts_id = str(uuid.uuid4())
    if client is None:
        return facts_id

    try:
        payload = {
            "id": facts_id,
            "request_id": request_id,
            "diagnosis": patient_data.get("diagnosis"),
            "icd10_code": patient_data.get("icd10_code"),
            "requested_service": patient_data.get("requested_service"),
            "cpt_hcpcs_code": patient_data.get("cpt_hcpcs_code"),
            "severity": patient_data.get("severity"),
            "severity_evidence": patient_data.get("severity_evidence") or [],
            "previous_treatment": patient_data.get("previous_treatment") or [],
            "documentation": patient_data.get("documentation") or {},
            "clinical_information": patient_data.get("clinical_information") or {},
            "model_name": model_name,
            "extraction_status": "SUCCESS"
        }

        try:
            response = client.table("clinical_facts").insert(payload).execute()
            if response.data and len(response.data) > 0:
                return response.data[0].get("id") or facts_id
        except Exception as p_err:
            min_payload = {
                "id": facts_id,
                "request_id": request_id,
                "diagnosis": patient_data.get("diagnosis"),
                "icd10_code": patient_data.get("icd10_code"),
                "requested_service": patient_data.get("requested_service"),
                "cpt_hcpcs_code": patient_data.get("cpt_hcpcs_code"),
                "severity": patient_data.get("severity"),
                "model_name": model_name,
                "extraction_status": "SUCCESS"
            }
            try:
                response = client.table("clinical_facts").insert(min_payload).execute()
                if response.data and len(response.data) > 0:
                    return response.data[0].get("id") or facts_id
            except Exception as e2:
                logger.debug(f"Minimal clinical facts insert notice: {e2}")
        return facts_id
    except Exception as e:
        logger.warning(f"Note: Could not insert clinical facts into Supabase (table may require schema update): {e}")
        return facts_id


def create_patient_insurance(
    patient_id: str,
    insurance_data: Dict[str, Any]
) -> Optional[str]:
    """
    Insert structured patient insurance record into 'patient_insurance' table.
    """
    if not patient_id or not insurance_data:
        return None

    import uuid
    client = get_supabase_client()
    ins_id = insurance_data.get("id") or str(uuid.uuid4())
    if client is None:
        return ins_id

    try:
        ins_number = insurance_data.get("insurance_number") or f"INS-{abs(hash(ins_id)) % 1000000:06d}"
        payload = {
            "id": ins_id,
            "patient_id": patient_id,
            "insurance_number": ins_number,
            "member_id": insurance_data.get("member_id"),
            "policy_id": insurance_data.get("policy_id"),
            "coverage_start_date": insurance_data.get("coverage_start_date") or "2024-01-01",
            "coverage_end_date": insurance_data.get("coverage_end_date"),
            "status": insurance_data.get("status") or "ACTIVE",
            "payer_name": insurance_data.get("payer_name") or insurance_data.get("payer"),
            "plan_name": insurance_data.get("plan_name")
        }

        response = client.table("patient_insurance").insert(payload).execute()
        if response.data and len(response.data) > 0:
            return response.data[0].get("id") or ins_id
        return ins_id
    except Exception as e:
        logger.warning(f"Note: Could not insert patient insurance into Supabase: {e}")
        return ins_id


def get_patient_insurance(patient_id: Optional[str]) -> List[Dict[str, Any]]:
    """
    Retrieve all insurance records for a given patient_id from Supabase database.
    Only returns actual records stored in the database for the requested patient.
    """
    if not patient_id:
        return []

    client = get_supabase_client()
    if client is None:
        return []

    try:
        response = client.table("patient_insurance").select("*").eq("patient_id", patient_id).execute()
        return response.data or []
    except Exception as e:
        logger.warning(f"Could not retrieve patient insurance from Supabase: {e}")
        return []


def get_active_patient_coverage(patient_id: str, request_date: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    Retrieve active insurance coverage record for a patient on request_date.
    """
    from src.patient_insurance import validate_patient_coverage
    records = get_patient_insurance(patient_id)
    val = validate_patient_coverage({"patient_id": patient_id}, insurance_records=records, request_date=request_date)
    return val.get("insurance") if val.get("is_valid") else None


def update_patient_insurance(insurance_id: str, update_data: Dict[str, Any]) -> bool:
    """
    Update an existing patient insurance record in Supabase.
    """
    if not insurance_id or not update_data:
        return False

    client = get_supabase_client()
    if client is None:
        return True

    try:
        response = client.table("patient_insurance").update(update_data).eq("id", insurance_id).execute()
        return bool(response.data)
    except Exception as e:
        logger.warning(f"Could not update patient insurance in Supabase: {e}")
        return False


def normalize_user_profile(user_rec: Dict[str, Any]) -> Dict[str, Any]:
    """Normalizes database row dictionary for compatibility with both schema column names and app keys."""
    if not user_rec:
        return {}

    prof = dict(user_rec)
    full_name = prof.get("full_name") or prof.get("name") or "Clinical User"
    clinical_role = prof.get("clinical_role") or prof.get("role") or "Clinical Reviewer"
    badge_label = prof.get("badge_label") or prof.get("badge") or "Clinical Reviewer"
    color_hex = prof.get("color_hex") or prof.get("color") or "#0f766e"

    prof["full_name"] = full_name
    prof["name"] = full_name
    prof["clinical_role"] = clinical_role
    prof["role"] = clinical_role
    prof["badge_label"] = badge_label
    prof["badge"] = badge_label
    prof["color_hex"] = color_hex
    prof["color"] = color_hex
    if "auth_id" not in prof:
        prof["auth_id"] = None
    return prof


def get_user_profile_by_auth_id(auth_id: str) -> Optional[Dict[str, Any]]:
    """
    Retrieve user profile record from Supabase 'user_profiles' by Supabase Auth UUID (auth_id).
    """
    if not auth_id:
        return None

    client = get_supabase_client()
    if client is None:
        return None

    try:
        response = client.table("user_profiles").select("*").eq("auth_id", auth_id).execute()
        if response.data and len(response.data) > 0:
            return normalize_user_profile(response.data[0])
    except Exception as e:
        logger.debug(f"Could not retrieve user profile by auth_id: {e}")

    return None


def get_user_profile_by_email(email: str) -> Optional[Dict[str, Any]]:
    """
    Retrieve user profile record from Supabase 'user_profiles' by email address.
    """
    if not email:
        return None

    clean_email = email.strip().lower()
    client = get_supabase_client()
    if client is None:
        return None

    try:
        response = client.table("user_profiles").select("*").eq("email", clean_email).execute()
        if response.data and len(response.data) > 0:
            return normalize_user_profile(response.data[0])
    except Exception as e:
        logger.debug(f"Could not retrieve user profile by email: {e}")

    return None


def get_or_link_user_profile(
    auth_user_id: str,
    email: str,
    name: Optional[str] = None,
    role: Optional[str] = None,
    username: Optional[str] = None
) -> Dict[str, Any]:
    """
    Reliable single helper to resolve or link user profiles in user_profiles table:
    1. Searches by auth_id.
    2. Fallbacks to search by email.
    3. Links existing profile by email when auth_id is missing/different (preventing duplicate rows).
    4. Creates a new profile only when genuinely missing.
    Never creates duplicates.
    """
    if not email:
        return {}

    clean_email = email.strip().lower()
    auth_id_str = str(auth_user_id) if auth_user_id else None

    # 1. Search DB by auth_id
    if auth_id_str:
        by_auth = get_user_profile_by_auth_id(auth_id_str)
        if by_auth:
            return by_auth

    # 2. Search DB by email
    by_email = get_user_profile_by_email(clean_email)
    if by_email:
        # Link auth_id if missing or different
        if auth_id_str and by_email.get("auth_id") != auth_id_str:
            by_email["auth_id"] = auth_id_str
            save_user_profile(by_email)
        return by_email

    # 3. Create missing profile
    name_parts = [p for p in (name or "").replace("Dr.", "").replace("MD", "").replace("RN", "").replace("CPC", "").replace("CHC", "").strip().split() if p]
    if len(name_parts) >= 2:
        initials = (name_parts[0][0] + name_parts[-1][0]).upper()
    elif len(name_parts) == 1:
        initials = name_parts[0][:2].upper()
    else:
        initials = clean_email[:2].upper()

    user_name = name.strip() if name else clean_email.split("@")[0].capitalize()
    user_role = role or "Senior Clinical Reviewer"
    user_uname = username or clean_email.split("@")[0]

    role_meta = {
        "Senior Clinical Reviewer": {"dept": "Prior Auth Operations", "badge": "Clinical Reviewer", "color": "#0f766e"},
        "Chief Medical Officer": {"dept": "Medical Affairs", "badge": "CMO / Approver", "color": "#1e3a8a"},
        "Prior Auth Specialist": {"dept": "Intake & Verification", "badge": "Auth Specialist", "color": "#0369a1"},
        "Compliance & Audit Manager": {"dept": "Regulatory Assurance", "badge": "Compliance Auditor", "color": "#b45309"},
        "Attending Physician / Reviewer": {"dept": "Clinical Practice", "badge": "Physician Reviewer", "color": "#0d9488"},
    }
    meta = role_meta.get(user_role, {"dept": "Clinical Operations", "badge": user_role, "color": "#0f766e"})

    new_prof = {
        "auth_id": auth_id_str,
        "email": clean_email,
        "username": user_uname,
        "full_name": user_name,
        "name": user_name,
        "clinical_role": user_role,
        "role": user_role,
        "department": meta["dept"],
        "initials": initials,
        "badge_label": meta["badge"],
        "badge": meta["badge"],
        "color_hex": meta["color"],
        "color": meta["color"],
    }

    rec_id = save_user_profile(new_prof)
    if rec_id:
        new_prof["id"] = rec_id

    return normalize_user_profile(new_prof)


def get_user_profiles_from_db() -> List[Dict[str, Any]]:
    """
    Retrieve all user profile records from the 'user_profiles' table in Supabase.
    """
    client = get_supabase_client()
    if client is None:
        return []

    try:
        response = client.table("user_profiles").select("*").execute()
        data = response.data or []
        return [normalize_user_profile(row) for row in data]
    except Exception as e:
        logger.warning(f"Could not retrieve user profiles from Supabase DB: {e}")
        return []


def save_user_profile(user_data: Dict[str, Any]) -> Optional[str]:
    """
    Insert or update a user profile record in 'user_profiles' using auth_id or email as identity.
    Does NOT store plaintext passwords. Supports both new and legacy table column schemas cleanly.
    """
    if not user_data or not user_data.get("email"):
        return None

    import uuid
    client = get_supabase_client()
    clean_email = str(user_data.get("email")).strip().lower()
    auth_id_val = user_data.get("auth_id")
    uid = user_data.get("id") or str(uuid.uuid4())

    if client is None:
        return uid

    full_name = user_data.get("full_name") or user_data.get("name") or "Clinical User"
    clinical_role = user_data.get("clinical_role") or user_data.get("role") or "Clinical Reviewer"
    department = user_data.get("department") or "Prior Auth Operations"
    initials = user_data.get("initials") or "CU"
    badge_label = user_data.get("badge_label") or user_data.get("badge") or "Clinical Reviewer"
    color_hex = user_data.get("color_hex") or user_data.get("color") or "#0f766e"
    username = str(user_data.get("username") or clean_email.split("@")[0]).strip().lower()

    # Formulate primary payload with new schema column names
    payload_new = {
        "id": uid,
        "email": clean_email,
        "username": username,
        "full_name": full_name,
        "clinical_role": clinical_role,
        "department": department,
        "initials": initials,
        "badge_label": badge_label,
        "color_hex": color_hex,
        "password": "", # Placeholder to satisfy PostgreSQL NOT NULL constraint if present
    }
    if auth_id_val:
        payload_new["auth_id"] = auth_id_val

    # Formulate legacy payload with legacy column names
    payload_legacy = {
        "id": uid,
        "email": clean_email,
        "username": username,
        "name": full_name,
        "role": clinical_role,
        "department": department,
        "initials": initials,
        "badge": badge_label,
        "color": color_hex,
        "password": "",
    }
    if auth_id_val:
        payload_legacy["auth_id"] = auth_id_val

    payload_new_no_auth = {k: v for k, v in payload_new.items() if k != "auth_id"}
    payload_legacy_no_auth = {k: v for k, v in payload_legacy.items() if k != "auth_id"}

    # 1. Check if profile already exists in DB by auth_id or email
    existing = None
    if auth_id_val:
        existing = get_user_profile_by_auth_id(auth_id_val)
    if not existing:
        existing = get_user_profile_by_email(clean_email)

    if existing and existing.get("id"):
        db_id = existing["id"]
        # Update existing record
        for p in (payload_new, payload_legacy, payload_new_no_auth, payload_legacy_no_auth):
            try:
                update_payload = {k: v for k, v in p.items() if k != "id"}
                res = client.table("user_profiles").update(update_payload).eq("id", db_id).execute()
                if res.data and len(res.data) > 0:
                    logger.info(f"User profile updated for {clean_email}")
                    return db_id
            except Exception as e:
                logger.debug(f"Update user_profile attempt failed: {e}")
        return db_id
    else:
        # Insert new record
        for p in (payload_new, payload_legacy, payload_new_no_auth, payload_legacy_no_auth):
            try:
                res = client.table("user_profiles").insert(p).execute()
                if res.data and len(res.data) > 0:
                    logger.info(f"User profile inserted for {clean_email}")
                    return res.data[0].get("id") or uid
            except Exception as e:
                logger.debug(f"Insert user_profile attempt failed: {e}")

    return uid


def seed_initial_user_profiles_to_db() -> bool:
    """
    Seeds initial clinical user profiles into Supabase 'user_profiles' table if empty.
    """
    client = get_supabase_client()
    if client is None:
        return False

    try:
        existing = get_user_profiles_from_db()
        if existing:
            return True

        from src.auth import INITIAL_CLINICAL_PROFILES
        for prof in INITIAL_CLINICAL_PROFILES.values():
            save_user_profile(prof)
        return True
    except Exception as e:
        logger.warning(f"Could not seed initial user profiles to Supabase: {e}")
        return False





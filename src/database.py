import os
import logging
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
    client = get_supabase_client()
    if client is None:
        return None

    try:
        # Prepare data adhering to table schema
        payload = {
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
            inserted_id = response.data[0].get("id")
            logger.info(f"Patient saved successfully with ID: {inserted_id}")
            return inserted_id
        return None
    except Exception as e:
        logger.error(f"Error saving patient to Supabase: {e}")
        return None


def create_authorization_request(
    patient_record_id: Optional[str],
    patient_data: Dict[str, Any],
    status: str = "PENDING"
) -> Optional[str]:
    """
    Insert a prior authorization request into 'authorization_requests'.
    Returns the created request UUID on success, or None on failure.
    """
    client = get_supabase_client()
    if client is None:
        return None

    try:
        payload = {
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
            request_id = response.data[0].get("id")
            logger.info(f"Authorization request created with ID: {request_id}")
            return request_id
        return None
    except Exception as e:
        logger.error(f"Error creating authorization request in Supabase: {e}")
        return None


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
    client = get_supabase_client()
    if client is None:
        return None

    try:
        payload = {
            "request_id": request_id,
            "policy_id": decision_result.get("policy_id") or decision_result.get("applied_policy_id"),
            "policy_name": decision_result.get("policy_name") or decision_result.get("applied_policy_name"),
            "final_decision": decision_result.get("decision", "MANUAL REVIEW"),
            "failed_criteria": decision_result.get("failed_criteria") or [],
            "manual_review_reasons": decision_result.get("manual_review_reasons") or [],
        }

        response = client.table("decisions").insert(payload).execute()
        if response.data and len(response.data) > 0:
            decision_id = response.data[0].get("id")
            logger.info(f"Decision saved with ID: {decision_id}")
            return decision_id
        return None
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
    Fetch recent authorization requests with linked patient and decision data.
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
        return response.data or []

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




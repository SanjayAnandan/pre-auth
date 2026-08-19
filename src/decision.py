# src/decision.py

import json
import logging
from typing import Any, Dict, List, Optional

from src.policy_matcher import find_matching_policies, normalize_code, normalize_payer
from src.normalizer import normalize_patient
from src.rule_engine import evaluate_policy

logger = logging.getLogger(__name__)


# ============================================================
# LOAD NO PRIOR AUTHORIZATION LIST
# ============================================================

def load_no_prior_auth(path):
    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)


# ============================================================
# DETERMINISTIC POLICY SELECTION
# ============================================================

def select_policy_deterministically(patient: Dict[str, Any], matching_policies: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Deterministically select the best matching policy when multiple match:
    1. Prefer exact payer match.
    2. Sort deterministically by policy_id.
    """
    if len(matching_policies) == 1:
        return matching_policies[0]

    patient_payer = normalize_payer(patient.get("payer"))

    # Rank 1: Filter policies with exact payer match
    exact_payer_matches = [
        p for p in matching_policies
        if patient_payer and normalize_payer(p.get("payer")) == patient_payer
    ]

    if len(exact_payer_matches) == 1:
        return exact_payer_matches[0]
    elif len(exact_payer_matches) > 1:
        pool = exact_payer_matches
    else:
        pool = matching_policies

    # Rank 2: Sort pool deterministically by policy_id
    sorted_policies = sorted(pool, key=lambda p: str(p.get("policy_id", "")))
    return sorted_policies[0]


# ============================================================
# PROCESS DECISION
# ============================================================

def process_decision(
    patient: Dict[str, Any],
    policies: List[Dict[str, Any]],
    no_pa_codes: List[str]
) -> Dict[str, Any]:

    doc_hash = patient.get("_document_hash") or "N/A"
    raw_code = patient.get("cpt_hcpcs_code")
    norm_code = normalize_code(raw_code)

    # Normalize no_pa_codes list
    norm_no_pa_list = [normalize_code(c) for c in no_pa_codes]

    # ========================================================
    # STEP 1 — NO PRIOR AUTH
    # ========================================================

    if norm_code and norm_code in norm_no_pa_list:
        trace_msg = f"""
========================================
AUTHORIZATION EVALUATION TRACE
========================================
Document Hash: {doc_hash}
CPT/HCPCS: {raw_code} (Normalized: {norm_code})
Diagnosis: {patient.get("diagnosis")}
Determination: NO_PRIOR_AUTH_REQUIRED
Reason: Requested service is present in no-prior-authorization list.
========================================
"""
        logger.info(trace_msg)
        print(trace_msg)

        return {
            "document_hash": doc_hash,
            "decision": "NO_PRIOR_AUTH_REQUIRED",
            "patient_id": patient.get("patient_id"),
            "code": raw_code,
            "reason": "Requested service is present in the no-prior-authorization list."
        }

    # ========================================================
    # STEP 2 — FIND APPLICABLE POLICIES
    # ========================================================

    matching_policies = find_matching_policies(patient, policies)

    if not matching_policies:
        trace_msg = f"""
========================================
AUTHORIZATION EVALUATION TRACE
========================================
Document Hash: {doc_hash}
CPT/HCPCS: {raw_code}
Diagnosis: {patient.get("diagnosis")}
Determination: MANUAL REVIEW
Reason: No applicable policy was found for requested service.
========================================
"""
        logger.info(trace_msg)
        print(trace_msg)

        return {
            "document_hash": doc_hash,
            "decision": "MANUAL REVIEW",
            "patient_id": patient.get("patient_id"),
            "code": raw_code,
            "reason": "No applicable policy was found for the requested service."
        }

    # ========================================================
    # STEP 3 — DETERMINISTIC POLICY SELECTION
    # ========================================================

    policy = select_policy_deterministically(patient, matching_policies)

    # ========================================================
    # STEP 3.5 — POLICY ACTIVE STATUS CHECK
    # ========================================================

    raw_status = policy.get("policy_status")
    is_active = raw_status is not None and str(raw_status).strip().lower() == "active"

    if not is_active:
        pol_id = policy.get("policy_id", "Unknown")
        status_str = str(raw_status).upper() if raw_status is not None else "MISSING"
        reason_msg = f"Policy {pol_id} is currently inactive and cannot be used for authorization evaluation."

        trace_msg = f"""
========================================
AUTHORIZATION EVALUATION TRACE
========================================
Document Hash:
{doc_hash}

CPT/HCPCS:
{raw_code}

Diagnosis:
{patient.get("diagnosis")}

Policy Retrieved: {pol_id}
Policy Status: {status_str}
Evaluation: NOT PERFORMED
Reason: Policy is inactive

Determination: MANUAL REVIEW
========================================
"""
        logger.info(trace_msg)
        print(trace_msg)

        return {
            "document_hash": doc_hash,
            "decision": "MANUAL REVIEW",
            "patient_id": patient.get("patient_id"),
            "requested_service": patient.get("requested_service"),
            "code": raw_code,
            "policy_id": pol_id,
            "policy_name": policy.get("policy_name"),
            "policy": policy,
            "normalized_patient": patient,
            "reason": reason_msg,
            "criteria": [],
            "results": [],
            "failed_criteria": [],
            "manual_review_reasons": [reason_msg]
        }

    # ========================================================
    # STEP 4 — POLICY-AWARE NORMALIZATION
    # ========================================================

    normalized_patient = normalize_patient(patient, policy)

    # ========================================================
    # STEP 5 — RULE ENGINE EVALUATION
    # ========================================================

    result = evaluate_policy(normalized_patient, policy)

    # ========================================================
    # STEP 6 — LOG DETERMINISTIC EVALUATION TRACE
    # ========================================================

    criteria_summary = "\n".join([
        f"- {res.get('criterion')}: {res.get('status')} ({res.get('reason')})"
        for res in result.get("results", [])
    ])

    trace_msg = f"""
========================================
AUTHORIZATION EVALUATION TRACE
========================================
Document Hash:
{doc_hash}

CPT/HCPCS:
{normalized_patient.get('cpt_hcpcs_code')}

Diagnosis:
{normalized_patient.get('diagnosis')}

Selected Policy:
{policy.get('policy_id')} - {policy.get('policy_name')}

Criteria Breakdown:
{criteria_summary}

Final Decision:
{result.get('decision')}
========================================
"""
    logger.info(trace_msg)
    print(trace_msg)

    # Add metadata to result
    result["document_hash"] = doc_hash
    result["patient_id"] = normalized_patient.get("patient_id")
    result["requested_service"] = normalized_patient.get("requested_service")
    result["code"] = normalized_patient.get("cpt_hcpcs_code")
    result["normalized_patient"] = normalized_patient
    result["policy"] = policy

    return result
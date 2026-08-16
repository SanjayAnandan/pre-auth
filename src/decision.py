# src/decision.py

import json

from src.policy_matcher import find_matching_policies
from src.normalizer import normalize_patient
from src.rule_engine import evaluate_policy


# ============================================================
# LOAD NO PRIOR AUTHORIZATION LIST
# ============================================================

def load_no_prior_auth(path):

    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)


# ============================================================
# PROCESS DECISION
# ============================================================

def process_decision(
    patient,
    policies,
    no_pa_codes
):

    code = patient.get(
        "cpt_hcpcs_code"
    )

    # ========================================================
    # STEP 1 — NO PRIOR AUTH
    # ========================================================

    if code in no_pa_codes:

        return {
            "decision": "NO_PRIOR_AUTH_REQUIRED",
            "patient_id": patient.get("patient_id"),
            "code": code,
            "reason": (
                "Requested service is present in "
                "the no-prior-authorization list."
            )
        }

    # ========================================================
    # STEP 2 — FIND APPLICABLE POLICY
    # ========================================================

    matching_policies = find_matching_policies(
        patient,
        policies
    )

    if not matching_policies:

        return {
            "decision": "MANUAL_REVIEW",
            "patient_id": patient.get("patient_id"),
            "code": code,
            "reason": (
                "No applicable policy was found "
                "for the requested service."
            )
        }

    # ========================================================
    # STEP 3 — USE FIRST APPLICABLE POLICY
    # ========================================================

    policy = matching_policies[0]

    # ========================================================
    # STEP 4 — POLICY-AWARE NORMALIZATION
    # ========================================================

    normalized_patient = normalize_patient(
        patient,
        policy
    )

    # ========================================================
    # STEP 5 — RULE ENGINE
    # ========================================================

    result = evaluate_policy(
        normalized_patient,
        policy
    )

    # ========================================================
    # STEP 6 — ADD REQUEST INFORMATION
    # ========================================================

    result["patient_id"] = normalized_patient.get(
        "patient_id"
    )

    result["requested_service"] = normalized_patient.get(
        "requested_service"
    )

    result["code"] = normalized_patient.get(
        "cpt_hcpcs_code"
    )

    result["normalized_patient"] = normalized_patient

    result["policy"] = policy

    return result
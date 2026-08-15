import json

from src.policy_matcher import find_matching_policies
from src.rule_engine import evaluate_policy

def load_no_prior_auth(path):

    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)


def process_decision(patient, policies, no_pa_codes):

    code = patient.get("cpt_hcpcs_code")

    # ------------------------------------------------
    # STEP 1: Check whether prior authorization is
    #         required at all.
    # ------------------------------------------------

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

    # ------------------------------------------------
    # STEP 2: Find applicable policies
    # ------------------------------------------------

    matching_policies = find_matching_policies(
        patient,
        policies
    )

    # ------------------------------------------------
    # STEP 3: No matching policy
    # ------------------------------------------------

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

    # ------------------------------------------------
    # STEP 4: Evaluate first matching policy
    # ------------------------------------------------

    result = evaluate_policy(
        patient,
        matching_policies[0]
    )

    result["patient_id"] = patient.get("patient_id")
    result["requested_service"] = patient.get(
        "requested_service"
    )
    result["code"] = code

    return result
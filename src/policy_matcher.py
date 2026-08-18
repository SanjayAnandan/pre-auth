import json
import re
from typing import Any, Dict, List, Optional


def load_policies(path):
    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)


def normalize_code(value: Any) -> str:
    """
    Normalize CPT / HCPCS codes for policy matching:
    - convert to string
    - strip whitespace
    - uppercase
    - remove harmless formatting characters (dots, hyphens, spaces)
    """
    if value is None:
        return ""
    text = str(value).strip().upper()
    text = re.sub(r'[\s\-\.]', '', text)
    return text


def normalize_payer(value: Any) -> str:
    """
    Normalize payer names for policy matching:
    - convert to string
    - strip whitespace
    - lowercase
    - strip punctuation
    """
    if value is None:
        return ""
    text = str(value).strip().lower()
    text = re.sub(r'[\.\,\-\_\'\"]', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def find_matching_policies(patient: Dict[str, Any], policies: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Find all policies matching the patient's normalized CPT/HCPCS code and payer.
    """
    patient_code = normalize_code(patient.get("cpt_hcpcs_code"))
    patient_payer = normalize_payer(patient.get("payer"))

    matches = []

    for policy in policies:
        policy_codes = [
            normalize_code(code)
            for code in policy.get("cpt_hcpcs_codes", [])
        ]
        policy_payer = normalize_payer(policy.get("payer", ""))

        code_matches = bool(patient_code and patient_code in policy_codes)

        payer_matches = (
            not patient_payer
            or not policy_payer
            or policy_payer == patient_payer
            or policy_payer in patient_payer
            or patient_payer in policy_payer
        )

        if code_matches and payer_matches:
            matches.append(policy)

    return matches
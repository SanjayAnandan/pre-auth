import json


def load_policies(path):

    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)


def find_matching_policies(patient, policies):

    patient_code = patient.get("cpt_hcpcs_code")
    patient_payer = patient.get("payer")

    matches = []

    for policy in policies:

        policy_codes = [
            code.upper()
            for code in policy.get("cpt_hcpcs_codes", [])
        ]

        policy_payer = policy.get("payer", "").strip().lower()

        code_matches = patient_code in policy_codes

        payer_matches = (
            patient_payer is None
            or policy_payer == patient_payer.lower()
        )

        if code_matches and payer_matches:
            matches.append(policy)

    return matches
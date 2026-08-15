def normalize_string(value):

    if value is None:
        return None

    return " ".join(value.strip().lower().split())


def normalize_code(value):

    if value is None:
        return None

    return value.strip().upper()


def normalize_patient(patient):

    normalized = patient.copy()

    string_fields = [
        "patient_id",
        "patient_name",
        "gender",
        "payer",
        "diagnosis",
        "severity",
        "previous_treatment",
        "previous_procedure",
        "requested_service",
        "frequency",
        "provider_specialty",
        "facility_type"
    ]

    for field in string_fields:
        if field in normalized:
            normalized[field] = normalize_string(
                normalized[field]
            )

    normalized["icd10_code"] = normalize_code(
        normalized.get("icd10_code")
    )

    normalized["cpt_hcpcs_code"] = normalize_code(
        normalized.get("cpt_hcpcs_code")
    )

    return normalized
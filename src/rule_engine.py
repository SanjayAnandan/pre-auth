from typing import Any, Dict, List, Optional


# ============================================================
# BASIC HELPERS
# ============================================================

def normalize(value) -> str:
    """
    Convert a value to a deterministic comparison string.
    """

    if value is None:
        return ""

    text = str(value).strip().lower()

    text = text.replace("_", " ")
    text = text.replace("-", " ")

    # Collapse multiple spaces
    text = " ".join(
        text.split()
    )

    return text


def to_number(value):
    """
    Safely convert a value to a number.
    """

    if value is None:
        return None

    if isinstance(value, bool):
        return None

    try:

        number = float(value)

        if number.is_integer():
            return int(number)

        return number

    except (
        TypeError,
        ValueError
    ):
        return None


# ============================================================
# CANONICAL CLINICAL VOCABULARY
# ============================================================

def canonical_treatment(value) -> str:
    """
    Convert treatment terminology into a canonical form.

    This is deterministic and intentionally small.
    """

    text = normalize(value)

    aliases = {

        # Medication
        "medication": "medication",
        "medications": "medication",
        "medicine": "medication",
        "medicines": "medication",
        "drug therapy": "medication",
        "pharmacologic therapy": "medication",

        # Physical therapy
        "physical therapy": "physical therapy",
        "physiotherapy": "physical therapy",
        "pt": "physical therapy",

        # Activity modification
        "activity modification": "activity modification",
        "activity modifications": "activity modification",
        "modified activity": "activity modification"
    }

    return aliases.get(
        text,
        text
    )


def canonical_provider_specialty(
    value
) -> str:

    text = normalize(value)

    aliases = {

        "orthopedics": "orthopedics",
        "orthopedic": "orthopedics",
        "orthopedic surgery": "orthopedics",
        "orthopaedics": "orthopedics",
        "orthopaedic surgery": "orthopedics",

        "sports medicine": "sports medicine",

        "cardiology": "cardiology",
        "cardiologist": "cardiology",

        "oncology": "oncology",
        "oncologist": "oncology"
    }

    return aliases.get(
        text,
        text
    )


def canonical_facility_type(
    value
) -> str:

    text = normalize(value)

    aliases = {

        "hospital": "hospital",

        "imaging center": "imaging center",
        "imaging centre": "imaging center",

        "outpatient diagnostic center":
            "outpatient diagnostic center",

        "outpatient diagnostic centre":
            "outpatient diagnostic center",

        "diagnostic imaging center":
            "imaging center"
    }

    return aliases.get(
        text,
        text
    )


# ============================================================
# CPT / HCPCS
# ============================================================

def check_cpt_hcpcs(
    patient: Dict[str, Any],
    policy: Dict[str, Any]
):

    patient_code = normalize(
        patient.get(
            "cpt_hcpcs_code"
        )
    )

    policy_codes = [
        normalize(code)
        for code in policy.get(
            "cpt_hcpcs_codes",
            []
        )
    ]

    if not patient_code:

        return {
            "criterion": "CPT/HCPCS",
            "status": "FAILED",
            "reason": (
                "CPT/HCPCS code is missing."
            )
        }

    if patient_code in policy_codes:

        return {
            "criterion": "CPT/HCPCS",
            "status": "PASSED",
            "reason": (
                f"CPT/HCPCS {patient_code} "
                "is covered by the policy."
            )
        }

    return {
        "criterion": "CPT/HCPCS",
        "status": "FAILED",
        "reason": (
            f"CPT/HCPCS {patient_code} "
            "is not covered by the policy."
        )
    }


# ============================================================
# DIAGNOSIS
# ============================================================

def check_diagnosis(
    patient: Dict[str, Any],
    policy: Dict[str, Any]
):

    patient_code = normalize(
        patient.get(
            "icd10_code"
        )
    )

    policy_codes = [
        normalize(code)
        for code in policy.get(
            "icd10_codes",
            []
        )
    ]

    if not patient_code:

        return {
            "criterion": "Diagnosis",
            "status": "FAILED",
            "reason": (
                "ICD-10 code is missing."
            )
        }

    if patient_code in policy_codes:

        return {
            "criterion": "Diagnosis",
            "status": "PASSED",
            "reason": (
                f"ICD-10 {patient_code} "
                "is covered by the policy."
            )
        }

    # Fallback text comparison is deliberately secondary.
    diagnosis = normalize(
        patient.get(
            "diagnosis"
        )
    )

    covered_diagnoses = [
        normalize(item)
        for item in policy.get(
            "covered_diagnoses",
            []
        )
    ]

    if (
        diagnosis
        and diagnosis in covered_diagnoses
    ):

        return {
            "criterion": "Diagnosis",
            "status": "PASSED",
            "reason": (
                f"Diagnosis '{patient.get('diagnosis')}' "
                "matches the policy."
            )
        }

    return {
        "criterion": "Diagnosis",
        "status": "FAILED",
        "reason": (
            f"ICD-10 {patient_code} "
            "is not covered by the policy."
        )
    }


# ============================================================
# AGE
# ============================================================

def check_age(
    patient: Dict[str, Any],
    policy: Dict[str, Any]
):

    requirement = policy.get(
        "age_requirement"
    )

    if not requirement:

        return {
            "criterion": "Age",
            "status": "NOT_APPLICABLE",
            "reason": (
                "No age requirement."
            )
        }

    if not requirement.get(
        "required",
        False
    ):

        return {
            "criterion": "Age",
            "status": "NOT_APPLICABLE",
            "reason": (
                "Age requirement is not required."
            )
        }

    age = to_number(
        patient.get(
            "age"
        )
    )

    if age is None:

        return {
            "criterion": "Age",
            "status": "FAILED",
            "reason": (
                "Patient age is missing."
            )
        }

    minimum = to_number(
        requirement.get(
            "minimum_age"
        )
    )

    maximum = to_number(
        requirement.get(
            "maximum_age"
        )
    )

    if (
        minimum is not None
        and age < minimum
    ):

        return {
            "criterion": "Age",
            "status": "FAILED",
            "reason": (
                f"Patient age {age:g} "
                f"is below minimum age "
                f"{minimum:g}."
            )
        }

    if (
        maximum is not None
        and age > maximum
    ):

        return {
            "criterion": "Age",
            "status": "FAILED",
            "reason": (
                f"Patient age {age:g} "
                f"exceeds maximum age "
                f"{maximum:g}."
            )
        }

    return {
        "criterion": "Age",
        "status": "PASSED",
        "reason": (
            f"Patient age {age:g} "
            "satisfies the policy."
        )
    }


# ============================================================
# SEVERITY
# ============================================================

def check_severity(
    patient: Dict[str, Any],
    policy: Dict[str, Any]
):

    requirement = policy.get(
        "severity_requirement"
    )

    if not requirement:

        return {
            "criterion": "Severity",
            "status": "NOT_APPLICABLE",
            "reason": (
                "No severity requirement."
            )
        }

    if not requirement.get(
        "required",
        False
    ):

        return {
            "criterion": "Severity",
            "status": "NOT_APPLICABLE",
            "reason": (
                "Severity is not required."
            )
        }

    severity = normalize(
        patient.get(
            "severity"
        )
    )

    allowed = [
        normalize(level)
        for level in requirement.get(
            "allowed_levels",
            []
        )
    ]

    if not severity:

        return {
            "criterion": "Severity",
            "status": "FAILED",
            "reason": (
                "Patient severity was not provided."
            )
        }

    if severity not in allowed:

        return {
            "criterion": "Severity",
            "status": "FAILED",
            "reason": (
                f"Severity '{patient.get('severity')}' "
                "does not satisfy the policy."
            )
        }

    # --------------------------------------------------------
    # Functional impairment
    # --------------------------------------------------------

    if requirement.get(
        "functional_impairment_required",
        False
    ):

        clinical_information = patient.get(
            "clinical_information",
            {}
        )

        if not isinstance(
            clinical_information,
            dict
        ):
            clinical_information = {}

        functional = clinical_information.get(
            "functional_impairment"
        )

        if functional is not True:

            return {
                "criterion": "Severity",
                "status": "FAILED",
                "reason": (
                    "Required functional impairment "
                    "is not documented."
                )
            }

    return {
        "criterion": "Severity",
        "status": "PASSED",
        "reason": (
            f"Severity '{patient.get('severity')}' "
            "satisfies the policy."
        )
    }


# ============================================================
# PREVIOUS TREATMENT
# ============================================================

def check_previous_treatment(
    patient: Dict[str, Any],
    policy: Dict[str, Any]
):

    requirement = policy.get(
        "previous_treatment_requirement"
    )

    if not requirement:

        return {
            "criterion": "Previous Treatment",
            "status": "NOT_APPLICABLE",
            "reason": (
                "No previous treatment requirement."
            )
        }

    if not requirement.get(
        "required",
        False
    ):

        return {
            "criterion": "Previous Treatment",
            "status": "NOT_APPLICABLE",
            "reason": (
                "Previous treatment is not required."
            )
        }

    previous = patient.get(
        "previous_treatment",
        []
    )

    if not isinstance(
        previous,
        list
    ):

        return {
            "criterion": "Previous Treatment",
            "status": "FAILED",
            "reason": (
                "Previous treatment information "
                "has an invalid structure."
            )
        }

    if not previous:

        return {
            "criterion": "Previous Treatment",
            "status": "FAILED",
            "reason": (
                "Required previous treatment "
                "was not found."
            )
        }

    acceptable = requirement.get(
        "acceptable_treatments",
        []
    )

    minimum_duration = to_number(
        requirement.get(
            "minimum_duration_days",
            0
        )
    )

    if minimum_duration is None:
        minimum_duration = 0

    match_mode = normalize(
        requirement.get(
            "match_mode",
            "ANY"
        )
    ).upper()

    # --------------------------------------------------------
    # Policy has no treatment restrictions
    # --------------------------------------------------------

    if not acceptable:

        return {
            "criterion": "Previous Treatment",
            "status": "PASSED",
            "reason": (
                "Previous treatment is documented "
                "and no specific treatment type "
                "is required."
            )
        }

    acceptable_map = {}

    for treatment in acceptable:

        canonical = canonical_treatment(
            treatment
        )

        acceptable_map[
            canonical
        ] = treatment

    matched = []

    for item in previous:

        if not isinstance(
            item,
            dict
        ):
            continue

        treatment = item.get(
            "treatment"
        )

        duration = item.get(
            "duration_days"
        )

        if not treatment:
            continue

        canonical = canonical_treatment(
            treatment
        )

        if canonical not in acceptable_map:
            continue

        duration_value = to_number(
            duration
        )

        if duration_value is None:
            continue

        if duration_value >= minimum_duration:

            matched.append(
                {
                    "patient_treatment": treatment,
                    "policy_treatment": (
                        acceptable_map[
                            canonical
                        ]
                    ),
                    "duration_days": duration_value
                }
            )

    # --------------------------------------------------------
    # ANY
    # --------------------------------------------------------

    if match_mode == "ANY":

        if matched:

            result = matched[0]

            return {
                "criterion": "Previous Treatment",
                "status": "PASSED",
                "reason": (
                    f"Previous treatment "
                    f"'{result['patient_treatment']}' "
                    f"was documented for "
                    f"{result['duration_days']:g} days. "
                    f"Minimum required duration is "
                    f"{minimum_duration:g} days."
                )
            }

        return {
            "criterion": "Previous Treatment",
            "status": "FAILED",
            "reason": (
                "No acceptable previous treatment "
                "satisfies the required duration. "
                f"Minimum duration: "
                f"{minimum_duration:g} days."
            )
        }

    # --------------------------------------------------------
    # ALL
    # --------------------------------------------------------

    if match_mode == "ALL":

        matched_policy_types = {
            item["policy_treatment"]
            for item in matched
        }

        missing = [
            treatment
            for treatment in acceptable
            if treatment not in matched_policy_types
        ]

        if not missing:

            return {
                "criterion": "Previous Treatment",
                "status": "PASSED",
                "reason": (
                    "All required previous treatments "
                    "satisfy the policy."
                )
            }

        return {
            "criterion": "Previous Treatment",
            "status": "FAILED",
            "reason": (
                "The following required treatments "
                "do not satisfy the policy: "
                + ", ".join(missing)
            )
        }

    return {
        "criterion": "Previous Treatment",
        "status": "FAILED",
        "reason": (
            f"Unsupported treatment match mode: "
            f"{match_mode}"
        )
    }


# ============================================================
# PREVIOUS PROCEDURE
# ============================================================

def check_previous_procedure(
    patient: Dict[str, Any],
    policy: Dict[str, Any]
):

    requirement = policy.get(
        "previous_procedure_requirement"
    )

    if not requirement:

        return {
            "criterion": "Previous Procedure",
            "status": "NOT_APPLICABLE",
            "reason": (
                "No previous procedure requirement."
            )
        }

    procedures = patient.get(
        "previous_procedure",
        []
    )

    if not procedures:

        return {
            "criterion": "Previous Procedure",
            "status": "FAILED",
            "reason": (
                "Required previous procedure "
                "was not documented."
            )
        }

    return {
        "criterion": "Previous Procedure",
        "status": "PASSED",
        "reason": (
            "Required previous procedure "
            "is documented."
        )
    }


# ============================================================
# PROVIDER SPECIALTY
# ============================================================

def check_provider_specialty(
    patient: Dict[str, Any],
    policy: Dict[str, Any]
):

    required = policy.get(
        "provider_specialty_requirement"
    )

    if not required:

        return {
            "criterion": "Provider Specialty",
            "status": "NOT_APPLICABLE",
            "reason": (
                "No provider specialty requirement."
            )
        }

    patient_specialty = canonical_provider_specialty(
        patient.get(
            "provider_specialty"
        )
    )

    if not patient_specialty:

        return {
            "criterion": "Provider Specialty",
            "status": "FAILED",
            "reason": (
                "Provider specialty is missing."
            )
        }

    allowed = {
        canonical_provider_specialty(
            item
        )
        for item in required
    }

    if patient_specialty in allowed:

        return {
            "criterion": "Provider Specialty",
            "status": "PASSED",
            "reason": (
                f"Provider specialty "
                f"'{patient.get('provider_specialty')}' "
                "is eligible."
            )
        }

    return {
        "criterion": "Provider Specialty",
        "status": "FAILED",
        "reason": (
            f"Provider specialty "
            f"'{patient.get('provider_specialty')}' "
            "is not eligible."
        )
    }


# ============================================================
# FACILITY
# ============================================================

def check_facility(
    patient: Dict[str, Any],
    policy: Dict[str, Any]
):

    required = policy.get(
        "facility_type_requirement"
    )

    if not required:

        return {
            "criterion": "Facility",
            "status": "NOT_APPLICABLE",
            "reason": (
                "No facility requirement."
            )
        }

    patient_facility = canonical_facility_type(
        patient.get(
            "facility_type"
        )
    )

    if not patient_facility:

        return {
            "criterion": "Facility",
            "status": "FAILED",
            "reason": (
                "Facility type is missing."
            )
        }

    allowed = {
        canonical_facility_type(
            item
        )
        for item in required
    }

    if patient_facility in allowed:

        return {
            "criterion": "Facility",
            "status": "PASSED",
            "reason": (
                f"Facility '{patient.get('facility_type')}' "
                "is eligible."
            )
        }

    return {
        "criterion": "Facility",
        "status": "FAILED",
        "reason": (
            f"Facility '{patient.get('facility_type')}' "
            "is not eligible."
        )
    }


# ============================================================
# DOCUMENTATION
# ============================================================

def check_documentation(
    patient: Dict[str, Any],
    policy: Dict[str, Any]
):

    required_docs = policy.get(
        "documentation_requirement",
        []
    )

    if not required_docs:

        return {
            "criterion": "Documentation",
            "status": "NOT_APPLICABLE",
            "reason": (
                "No specific documentation "
                "requirements."
            )
        }

    documentation = patient.get(
        "documentation",
        {}
    )

    if not isinstance(
        documentation,
        dict
    ):
        documentation = {}

    # --------------------------------------------------------
    # Normalize documentation keys
    # --------------------------------------------------------

    normalized_documentation = {}

    for key, value in documentation.items():

        normalized_key = normalize(
            key
        )

        normalized_documentation[
            normalized_key
        ] = value

    missing_docs = []

    for required_doc in required_docs:

        required_key = normalize(
            required_doc
        )

        value = normalized_documentation.get(
            required_key
        )

        if value is not True:

            missing_docs.append(
                required_doc
            )

    # --------------------------------------------------------
    # PASS
    # --------------------------------------------------------

    if not missing_docs:

        return {
            "criterion": "Documentation",
            "status": "PASSED",
            "reason": (
                "All required documentation is present: "
                + ", ".join(required_docs)
            )
        }

    # --------------------------------------------------------
    # FAIL
    # --------------------------------------------------------

    return {
        "criterion": "Documentation",
        "status": "FAILED",
        "reason": (
            "Missing required documentation: "
            + ", ".join(missing_docs)
        )
    }


# ============================================================
# QUANTITY
# ============================================================

def check_quantity(
    patient: Dict[str, Any],
    policy: Dict[str, Any]
):

    requirement = policy.get(
        "quantity_limit"
    )

    if not requirement:

        return {
            "criterion": "Quantity",
            "status": "NOT_APPLICABLE",
            "reason": (
                "No quantity limit."
            )
        }

    maximum = to_number(
        requirement.get(
            "maximum_quantity"
        )
    )

    if maximum is None:

        return {
            "criterion": "Quantity",
            "status": "NOT_APPLICABLE",
            "reason": (
                "No valid quantity limit."
            )
        }

    quantity = to_number(
        patient.get(
            "quantity"
        )
    )

    if quantity is None:

        return {
            "criterion": "Quantity",
            "status": "FAILED",
            "reason": (
                "Requested quantity is missing."
            )
        }

    if quantity <= maximum:

        return {
            "criterion": "Quantity",
            "status": "PASSED",
            "reason": (
                f"Requested quantity {quantity:g} "
                f"is within the maximum allowed "
                f"quantity of {maximum:g}."
            )
        }

    return {
        "criterion": "Quantity",
        "status": "FAILED",
        "reason": (
            f"Requested quantity {quantity:g} "
            f"exceeds the maximum allowed "
            f"quantity of {maximum:g}."
        )
    }


# ============================================================
# FREQUENCY
# ============================================================

def check_frequency(
    patient: Dict[str, Any],
    policy: Dict[str, Any]
):

    requirement = policy.get(
        "frequency_limit"
    )

    if not requirement:

        return {
            "criterion": "Frequency",
            "status": "NOT_APPLICABLE",
            "reason": (
                "No frequency limit."
            )
        }

    frequency = patient.get(
        "frequency"
    )

    if not frequency:

        return {
            "criterion": "Frequency",
            "status": "NOT_APPLICABLE",
            "reason": (
                "No frequency was specified."
            )
        }

    return {
        "criterion": "Frequency",
        "status": "PASSED",
        "reason": (
            "Frequency information is documented."
        )
    }


# ============================================================
# POLICY EVALUATION
# ============================================================

def evaluate_policy(
    patient: Dict[str, Any],
    policy: Dict[str, Any]
) -> Dict[str, Any]:

    results = []

    results.append(
        check_cpt_hcpcs(
            patient,
            policy
        )
    )

    results.append(
        check_diagnosis(
            patient,
            policy
        )
    )

    results.append(
        check_age(
            patient,
            policy
        )
    )

    results.append(
        check_severity(
            patient,
            policy
        )
    )

    results.append(
        check_previous_treatment(
            patient,
            policy
        )
    )

    results.append(
        check_previous_procedure(
            patient,
            policy
        )
    )

    results.append(
        check_provider_specialty(
            patient,
            policy
        )
    )

    results.append(
        check_facility(
            patient,
            policy
        )
    )

    results.append(
        check_documentation(
            patient,
            policy
        )
    )

    results.append(
        check_quantity(
            patient,
            policy
        )
    )

    results.append(
        check_frequency(
            patient,
            policy
        )
    )

    # ========================================================
    # Determine final decision
    # ========================================================

    failed = [
        result
        for result in results
        if result["status"] == "FAILED"
    ]

    manual_review = []

    manual_review_criteria = policy.get(
        "manual_review_criteria",
        []
    )

    clinical_information = patient.get(
        "clinical_information",
        {}
    )

    if isinstance(
        clinical_information,
        dict
    ):

        contradictory = clinical_information.get(
            "contradictory_information"
        )

        if contradictory is True:

            manual_review.append(
                "Required clinical information is contradictory"
            )

    # --------------------------------------------------------
    # Final decision
    # --------------------------------------------------------

    if failed:

        decision = "DENIED"

    elif manual_review:

        decision = "MANUAL REVIEW"

    else:

        decision = "APPROVED"

    return {
        "decision": decision,
        "policy_id": policy.get(
            "policy_id"
        ),
        "policy_name": policy.get(
            "policy_name"
        ),
        "results": results,
        "failed_criteria": failed,
        "manual_review_reasons": manual_review
    }
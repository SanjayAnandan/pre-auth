# src/rule_engine.py

import re


# ============================================================
# Utility Functions
# ============================================================

def normalize(value):
    """
    Convert a value into a normalized lowercase string.
    Safely handles None, lists, dictionaries, etc.
    """
    if value is None:
        return ""

    if isinstance(value, list):
        return " ".join(normalize(v) for v in value)

    if isinstance(value, dict):
        return " ".join(
            f"{normalize(k)} {normalize(v)}"
            for k, v in value.items()
        )

    return str(value).strip().lower()


def to_number(value):
    """
    Safely convert a value to float.

    Returns None if conversion is impossible.
    """
    if value is None:
        return None

    if isinstance(value, bool):
        return None

    try:
        return float(value)
    except (TypeError, ValueError):
        pass

    # Extract first number from strings such as:
    # "6 visits"
    # "Maximum 6"
    # "6.0"
    match = re.search(r"\d+(?:\.\d+)?", str(value))

    if match:
        try:
            return float(match.group())
        except ValueError:
            return None

    return None


def as_list(value):
    """
    Convert a value into a list.
    """
    if value is None:
        return []

    if isinstance(value, list):
        return value

    if isinstance(value, tuple):
        return list(value)

    return [value]


def contains_match(patient_value, allowed_values):
    """
    Case-insensitive matching.

    Supports:
        exact matches
        partial matches
    """

    patient_text = normalize(patient_value)

    if not patient_text:
        return False

    for allowed in as_list(allowed_values):

        allowed_text = normalize(allowed)

        if not allowed_text:
            continue

        if (
            patient_text == allowed_text
            or allowed_text in patient_text
            or patient_text in allowed_text
        ):
            return True

    return False


# ============================================================
# Diagnosis
# ============================================================

def check_diagnosis(patient, policy):

    diagnosis = patient.get("diagnosis")

    covered = policy.get("covered_diagnoses", [])

    if not diagnosis:
        return {
            "criterion": "Diagnosis",
            "status": "FAILED",
            "reason": "Patient diagnosis was not provided."
        }

    if not covered:
        return {
            "criterion": "Diagnosis",
            "status": "NOT_APPLICABLE",
            "reason": "No diagnosis requirement is specified."
        }

    if contains_match(diagnosis, covered):

        return {
            "criterion": "Diagnosis",
            "status": "PASSED",
            "reason": (
                f"Diagnosis '{diagnosis}' "
                "is covered by the policy."
            )
        }

    return {
        "criterion": "Diagnosis",
        "status": "FAILED",
        "reason": (
            f"Diagnosis '{diagnosis}' "
            "is not covered."
        )
    }


# ============================================================
# ICD-10
# ============================================================

def check_icd10(patient, policy):

    patient_code = patient.get("icd10_code")

    allowed_codes = policy.get("icd10_codes", [])

    if not patient_code:
        return {
            "criterion": "ICD-10 Code",
            "status": "FAILED",
            "reason": "ICD-10 code was not provided."
        }

    if not allowed_codes:
        return {
            "criterion": "ICD-10 Code",
            "status": "NOT_APPLICABLE",
            "reason": "No ICD-10 requirement is specified."
        }

    patient_code = normalize(patient_code)

    normalized_codes = [
        normalize(code)
        for code in allowed_codes
    ]

    if patient_code in normalized_codes:

        return {
            "criterion": "ICD-10 Code",
            "status": "PASSED",
            "reason": (
                f"ICD-10 code {patient_code.upper()} "
                "is covered by the policy."
            )
        }

    return {
        "criterion": "ICD-10 Code",
        "status": "FAILED",
        "reason": (
            f"{patient_code.upper()} "
            "is not covered by this policy."
        )
    }


# ============================================================
# Age
# ============================================================

def check_age(patient, policy):

    age = to_number(patient.get("age"))

    requirement = policy.get("age_requirement")

    if not requirement:
        return {
            "criterion": "Age",
            "status": "NOT_APPLICABLE",
            "reason": "No age requirement is specified."
        }

    if age is None:
        return {
            "criterion": "Age",
            "status": "FAILED",
            "reason": "Patient age was not provided or is invalid."
        }

    minimum = to_number(
        requirement.get("minimum_age")
    )

    maximum = to_number(
        requirement.get("maximum_age")
    )

    if minimum is not None and age < minimum:

        return {
            "criterion": "Age",
            "status": "FAILED",
            "reason": (
                f"Patient age {age:g} is below "
                f"the minimum age of {minimum:g}."
            )
        }

    if maximum is not None and age > maximum:

        return {
            "criterion": "Age",
            "status": "FAILED",
            "reason": (
                f"Patient age {age:g} is above "
                f"the maximum age of {maximum:g}."
            )
        }

    return {
        "criterion": "Age",
        "status": "PASSED",
        "reason": "Patient age satisfies the policy."
    }


# ============================================================
# Severity
# ============================================================

def check_severity(patient, policy):

    requirement = policy.get("severity_requirement")

    if not requirement:
        return {
            "criterion": "Severity",
            "status": "NOT_APPLICABLE",
            "reason": "No severity requirement is specified."
        }

    patient_severity = normalize(
        patient.get("severity")
    )

    if not patient_severity:
        return {
            "criterion": "Severity",
            "status": "FAILED",
            "reason": "Patient severity was not provided."
        }

    allowed_levels = requirement.get(
        "allowed_levels",
        []
    )

    if allowed_levels:

        normalized_levels = [
            normalize(level)
            for level in allowed_levels
        ]

        if patient_severity not in normalized_levels:

            return {
                "criterion": "Severity",
                "status": "FAILED",
                "reason": (
                    f"Severity '{patient.get('severity')}' "
                    "does not satisfy the policy requirement."
                )
            }

    # --------------------------------------------------------
    # Functional impairment
    # --------------------------------------------------------

    if requirement.get(
        "functional_impairment_required"
    ):

        clinical = patient.get(
            "clinical_information",
            {}
        )

        if not isinstance(clinical, dict):
            clinical = {}

        functional = clinical.get(
            "functional_impairment"
        )

        if functional is not True:

            return {
                "criterion": "Severity",
                "status": "FAILED",
                "reason": (
                    "Functional impairment is required "
                    "but was not documented."
                )
            }

    # --------------------------------------------------------
    # Acute / worsening symptoms
    # --------------------------------------------------------

    if requirement.get(
        "acute_or_worsening_symptoms_required"
    ):

        clinical = patient.get(
            "clinical_information",
            {}
        )

        if not isinstance(clinical, dict):
            clinical = {}

        acute = clinical.get(
            "acute_or_worsening_symptoms"
        )

        if acute is not True:

            return {
                "criterion": "Severity",
                "status": "FAILED",
                "reason": (
                    "Acute or worsening symptoms "
                    "are required."
                )
            }

    # --------------------------------------------------------
    # Neurological symptoms
    # --------------------------------------------------------

    if requirement.get(
        "neurological_symptoms_acceptable"
    ):

        clinical = patient.get(
            "clinical_information",
            {}
        )

        if not isinstance(clinical, dict):
            clinical = {}

        # This requirement is permissive.
        # It does not automatically fail if symptoms
        # are absent.

    # --------------------------------------------------------
    # Acute neurological symptoms
    # --------------------------------------------------------

    if requirement.get(
        "acute_neurological_symptoms_required"
    ):

        clinical = patient.get(
            "clinical_information",
            {}
        )

        if not isinstance(clinical, dict):
            clinical = {}

        acute_neuro = clinical.get(
            "acute_neurological_symptoms"
        )

        if acute_neuro is not True:

            return {
                "criterion": "Severity",
                "status": "FAILED",
                "reason": (
                    "Acute neurological symptoms "
                    "are required."
                )
            }

    # --------------------------------------------------------
    # Cardiac clinical findings
    # --------------------------------------------------------

    if requirement.get(
        "clinical_symptoms_or_abnormal_findings_required"
    ):

        clinical = patient.get(
            "clinical_information",
            {}
        )

        if not isinstance(clinical, dict):
            clinical = {}

        finding = clinical.get(
            "clinical_symptoms_or_abnormal_findings"
        )

        if finding is not True:

            return {
                "criterion": "Severity",
                "status": "FAILED",
                "reason": (
                    "Clinical symptoms or abnormal findings "
                    "are required."
                )
            }

    # --------------------------------------------------------
    # Pathology confirmation
    # --------------------------------------------------------

    if requirement.get(
        "pathology_confirmation_required"
    ):

        clinical = patient.get(
            "clinical_information",
            {}
        )

        if not isinstance(clinical, dict):
            clinical = {}

        pathology = clinical.get(
            "pathology_confirmation"
        )

        if pathology is not True:

            return {
                "criterion": "Severity",
                "status": "FAILED",
                "reason": (
                    "Pathology confirmation "
                    "is required."
                )
            }

    return {
        "criterion": "Severity",
        "status": "PASSED",
        "reason": "Severity requirement satisfied."
    }


# ============================================================
# Previous Treatment
# ============================================================

def check_previous_treatment(patient, policy):

    requirement = policy.get(
        "previous_treatment_requirement"
    )

    if not requirement:

        return {
            "criterion": "Previous Treatment",
            "status": "NOT_APPLICABLE",
            "reason": "No previous treatment requirement."
        }

    required = requirement.get(
        "required",
        False
    )

    if not required:

        return {
            "criterion": "Previous Treatment",
            "status": "NOT_APPLICABLE",
            "reason": "Previous treatment is not required."
        }

    previous = patient.get(
        "previous_treatment"
    )

    if not previous:

        return {
            "criterion": "Previous Treatment",
            "status": "FAILED",
            "reason": "Required previous treatment was not found."
        }

    acceptable = requirement.get(
        "acceptable_treatments",
        []
    )

    # If policy doesn't specify acceptable treatments,
    # presence of previous treatment is sufficient.
    if not acceptable:

        return {
            "criterion": "Previous Treatment",
            "status": "PASSED",
            "reason": "Previous treatment is documented."
        }

    previous_text = normalize(previous)

    for treatment in acceptable:

        treatment_text = normalize(treatment)

        if (
            treatment_text in previous_text
            or previous_text in treatment_text
        ):

            return {
                "criterion": "Previous Treatment",
                "status": "PASSED",
                "reason": (
                    f"Previous treatment "
                    f"'{treatment}' is acceptable."
                )
            }

    return {
        "criterion": "Previous Treatment",
        "status": "FAILED",
        "reason": (
            "The documented previous treatment "
            "does not satisfy the policy requirement."
        )
    }


# ============================================================
# Previous Procedure
# ============================================================

def check_previous_procedure(patient, policy):

    requirement = policy.get(
        "previous_procedure_requirement"
    )

    if not requirement:

        return {
            "criterion": "Previous Procedure",
            "status": "NOT_APPLICABLE",
            "reason": "No previous procedure requirement."
        }

    if isinstance(requirement, dict):

        required = requirement.get(
            "required",
            False
        )

        procedures = requirement.get(
            "procedures",
            []
        )

    else:

        required = True
        procedures = as_list(requirement)

    if not required:

        return {
            "criterion": "Previous Procedure",
            "status": "NOT_APPLICABLE",
            "reason": "Previous procedure is not required."
        }

    previous = patient.get(
        "previous_procedure"
    )

    if not previous:

        return {
            "criterion": "Previous Procedure",
            "status": "FAILED",
            "reason": "Required previous procedure was not found."
        }

    if not procedures:

        return {
            "criterion": "Previous Procedure",
            "status": "PASSED",
            "reason": "Previous procedure is documented."
        }

    if contains_match(
        previous,
        procedures
    ):

        return {
            "criterion": "Previous Procedure",
            "status": "PASSED",
            "reason": "Required previous procedure is documented."
        }

    return {
        "criterion": "Previous Procedure",
        "status": "FAILED",
        "reason": (
            "The documented previous procedure "
            "does not satisfy the policy requirement."
        )
    }


# ============================================================
# Provider Specialty
# ============================================================

def check_provider_specialty(patient, policy):

    provider = patient.get(
        "provider_specialty"
    )

    allowed = policy.get(
        "provider_specialty_requirement",
        []
    )

    if not allowed:

        return {
            "criterion": "Provider Specialty",
            "status": "NOT_APPLICABLE",
            "reason": "No provider specialty requirement."
        }

    if not provider:

        return {
            "criterion": "Provider Specialty",
            "status": "FAILED",
            "reason": "Provider specialty was not provided."
        }

    if contains_match(
        provider,
        allowed
    ):

        return {
            "criterion": "Provider Specialty",
            "status": "PASSED",
            "reason": "Provider specialty is eligible."
        }

    return {
        "criterion": "Provider Specialty",
        "status": "FAILED",
        "reason": (
            f"Provider specialty '{provider}' "
            "is not eligible."
        )
    }


# ============================================================
# Facility Type
# ============================================================

def check_facility_type(patient, policy):

    facility = patient.get(
        "facility_type"
    )

    allowed = policy.get(
        "facility_type_requirement",
        []
    )

    if not allowed:

        return {
            "criterion": "Facility Type",
            "status": "NOT_APPLICABLE",
            "reason": "No facility type requirement."
        }

    if not facility:

        return {
            "criterion": "Facility Type",
            "status": "FAILED",
            "reason": "Facility type was not provided."
        }

    if contains_match(
        facility,
        allowed
    ):

        return {
            "criterion": "Facility Type",
            "status": "PASSED",
            "reason": "Facility type is eligible."
        }

    return {
        "criterion": "Facility Type",
        "status": "FAILED",
        "reason": (
            f"Facility type '{facility}' "
            "is not eligible."
        )
    }


# ============================================================
# Documentation
# ============================================================

def check_documentation(patient, policy):

    required_docs = policy.get(
        "documentation_requirement",
        []
    )

    if not required_docs:

        return {
            "criterion": "Documentation",
            "status": "NOT_APPLICABLE",
            "reason": "No specific documentation requirements."
        }

    complete = patient.get(
        "documentation_complete"
    )

    if complete is True:

        return {
            "criterion": "Documentation",
            "status": "PASSED",
            "reason": "Documentation is marked complete."
        }

    if isinstance(complete, str):

        if normalize(complete) in [
            "yes",
            "true",
            "complete",
            "completed"
        ]:

            return {
                "criterion": "Documentation",
                "status": "PASSED",
                "reason": "Documentation is marked complete."
            }

    return {
        "criterion": "Documentation",
        "status": "FAILED",
        "reason": (
            "Required documentation is not marked complete."
        )
    }


# ============================================================
# Quantity
# ============================================================

def check_quantity(patient, policy):

    patient_quantity = patient.get(
        "quantity"
    )

    # --------------------------------------------------------
    # Missing quantity
    # --------------------------------------------------------

    if patient_quantity is None:

        return {
            "criterion": "Quantity",
            "status": "NOT_APPLICABLE",
            "reason": "Requested quantity was not provided."
        }

    patient_quantity = to_number(
        patient_quantity
    )

    if patient_quantity is None:

        return {
            "criterion": "Quantity",
            "status": "NOT_APPLICABLE",
            "reason": (
                "Requested quantity could not be "
                "interpreted as a number."
            )
        }

    # --------------------------------------------------------
    # Policy limit
    # --------------------------------------------------------

    quantity_limit = policy.get(
        "quantity_limit"
    )

    if not quantity_limit:

        return {
            "criterion": "Quantity",
            "status": "NOT_APPLICABLE",
            "reason": "No quantity limit is specified."
        }

    if isinstance(
        quantity_limit,
        dict
    ):

        maximum = quantity_limit.get(
            "maximum_quantity"
        )

    else:

        maximum = quantity_limit

    maximum = to_number(
        maximum
    )

    if maximum is None:

        return {
            "criterion": "Quantity",
            "status": "NOT_APPLICABLE",
            "reason": (
                "Policy quantity limit "
                "could not be interpreted."
            )
        }

    # --------------------------------------------------------
    # Safe numeric comparison
    # --------------------------------------------------------

    if patient_quantity <= maximum:

        return {
            "criterion": "Quantity",
            "status": "PASSED",
            "reason": (
                f"Quantity {patient_quantity:g} "
                f"is within limit {maximum:g}."
            )
        }

    return {
        "criterion": "Quantity",
        "status": "FAILED",
        "reason": (
            f"Quantity {patient_quantity:g} "
            f"exceeds limit {maximum:g}."
        )
    }


# ============================================================
# Frequency
# ============================================================

def check_frequency(patient, policy):

    policy_frequency = policy.get(
        "frequency_limit"
    )

    if not policy_frequency:

        return {
            "criterion": "Frequency",
            "status": "NOT_APPLICABLE",
            "reason": "No frequency limit is specified."
        }

    patient_frequency = patient.get(
        "frequency"
    )

    if not patient_frequency:

        return {
            "criterion": "Frequency",
            "status": "NOT_APPLICABLE",
            "reason": "Patient frequency was not provided."
        }

    # --------------------------------------------------------
    # New structured policy format
    # --------------------------------------------------------

    if isinstance(
        policy_frequency,
        dict
    ):

        maximum_quantity = to_number(
            policy_frequency.get(
                "maximum_quantity"
            )
        )

        time_period_days = to_number(
            policy_frequency.get(
                "time_period_days"
            )
        )

        if (
            maximum_quantity is None
            or time_period_days is None
        ):

            return {
                "criterion": "Frequency",
                "status": "NOT_APPLICABLE",
                "reason": (
                    "Frequency policy is incomplete."
                )
            }

        patient_frequency_text = normalize(
            patient_frequency
        )

        # ----------------------------------------------------
        # Known frequency descriptions
        # ----------------------------------------------------

        frequency_days = None

        if "daily" in patient_frequency_text:
            frequency_days = 1

        elif (
            "weekly" in patient_frequency_text
            or "per week" in patient_frequency_text
        ):
            frequency_days = 7

        elif (
            "biweekly" in patient_frequency_text
            or "every 2 weeks" in patient_frequency_text
        ):
            frequency_days = 14

        elif (
            "monthly" in patient_frequency_text
            or "per month" in patient_frequency_text
        ):
            frequency_days = 30

        elif (
            "quarterly" in patient_frequency_text
        ):
            frequency_days = 90

        elif (
            "yearly" in patient_frequency_text
            or "annual" in patient_frequency_text
            or "annually" in patient_frequency_text
        ):
            frequency_days = 365

        else:

            match = re.search(
                r"(?:every|q)\s*(\d+)\s*days?",
                patient_frequency_text
            )

            if match:
                frequency_days = float(
                    match.group(1)
                )

        # ----------------------------------------------------
        # If frequency cannot be interpreted
        # ----------------------------------------------------

        if frequency_days is None:

            return {
                "criterion": "Frequency",
                "status": "NOT_APPLICABLE",
                "reason": (
                    f"Frequency '{patient_frequency}' "
                    "could not be normalized."
                )
            }

        # ----------------------------------------------------
        # Compare frequency
        #
        # A request is acceptable if it is no more frequent
        # than the policy allows.
        # ----------------------------------------------------

        if frequency_days >= time_period_days:

            return {
                "criterion": "Frequency",
                "status": "PASSED",
                "reason": (
                    "Frequency satisfies the policy limit."
                )
            }

        return {
            "criterion": "Frequency",
            "status": "FAILED",
            "reason": (
                f"Requested frequency '{patient_frequency}' "
                "is more frequent than the policy allows."
            )
        }

    # --------------------------------------------------------
    # Backward compatibility with string policies
    # --------------------------------------------------------

    policy_text = normalize(
        policy_frequency
    )

    patient_text = normalize(
        patient_frequency
    )

    if (
        patient_text == policy_text
        or patient_text in policy_text
        or policy_text in patient_text
    ):

        return {
            "criterion": "Frequency",
            "status": "PASSED",
            "reason": "Frequency matches policy."
        }

    return {
        "criterion": "Frequency",
        "status": "FAILED",
        "reason": (
            f"Frequency '{patient_frequency}' "
            "does not match policy."
        )
    }


# ============================================================
# Service / CPT / HCPCS
# ============================================================

def check_service(patient, policy):

    patient_code = normalize(
        patient.get("cpt_hcpcs_code")
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
            "criterion": "CPT / HCPCS",
            "status": "FAILED",
            "reason": "CPT / HCPCS code was not provided."
        }

    if not policy_codes:

        return {
            "criterion": "CPT / HCPCS",
            "status": "NOT_APPLICABLE",
            "reason": "No CPT / HCPCS codes are specified."
        }

    if patient_code in policy_codes:

        return {
            "criterion": "CPT / HCPCS",
            "status": "PASSED",
            "reason": (
                f"CPT / HCPCS code "
                f"{patient_code.upper()} "
                "matches the policy."
            )
        }

    return {
        "criterion": "CPT / HCPCS",
        "status": "FAILED",
        "reason": (
            f"CPT / HCPCS code "
            f"{patient_code.upper()} "
            "does not match the policy."
        )
    }


# ============================================================
# Evaluate Entire Policy
# ============================================================

def evaluate_policy(patient, policy):

    results = []

    # --------------------------------------------------------
    # Core policy checks
    # --------------------------------------------------------

    results.append(
        check_service(
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
        check_icd10(
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
        check_facility_type(
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
    # Determine decision
    # ========================================================

    failed = [
        result
        for result in results
        if result.get("status") == "FAILED"
    ]

    not_applicable = [
        result
        for result in results
        if result.get("status") == "NOT_APPLICABLE"
    ]

    # --------------------------------------------------------
    # Manual review criteria
    # --------------------------------------------------------

    manual_review = policy.get(
        "manual_review_criteria",
        []
    )

    manual_review_triggered = False

    # Contradictory / missing information can trigger review.
    #
    # We do NOT automatically send every NOT_APPLICABLE
    # result to manual review because some policies have
    # optional fields.
    if manual_review:

        clinical = patient.get(
            "clinical_information",
            {}
        )

        if isinstance(clinical, dict):

            if clinical.get(
                "contradictory_information"
            ) is True:

                manual_review_triggered = True

    # --------------------------------------------------------
    # Decision priority
    #
    # 1. Manual Review
    # 2. Denied
    # 3. Approved
    # --------------------------------------------------------

    if manual_review_triggered:

        decision = "MANUAL REVIEW"

    elif failed:

        decision = "DENIED"

    else:

        decision = "APPROVED"

    # --------------------------------------------------------
    # Build explanation
    # --------------------------------------------------------

    if decision == "APPROVED":

        explanation = (
            "The request satisfies the applicable "
            "requirements of the selected policy."
        )

    elif decision == "DENIED":

        explanation = (
            "The request does not satisfy one or more "
            "requirements of the selected policy."
        )

    else:

        explanation = (
            "The request requires additional manual review "
            "because the available information is "
            "insufficient or contradictory."
        )

    # --------------------------------------------------------
    # Return result
    # --------------------------------------------------------

    return {
        "decision": decision,
        "policy_id": policy.get(
            "policy_id"
        ),
        "policy_name": policy.get(
            "policy_name"
        ),
        "criteria": results,
        "failed_criteria": failed,
        "not_applicable_criteria": not_applicable,
        "patient_id": patient.get(
            "patient_id"
        ),
        "requested_service": patient.get(
            "requested_service"
        ),
        "code": patient.get(
            "cpt_hcpcs_code"
        ),
        "explanation": explanation
    }
# src/normalizer.py

import os
import json
from copy import deepcopy

from groq import Groq
from dotenv import load_dotenv


# ============================================================
# ENVIRONMENT
# ============================================================

load_dotenv()


# ============================================================
# GROQ CLIENT
# ============================================================

api_key = os.getenv("GROQ_API_KEY")

if not api_key:
    raise ValueError(
        "GROQ_API_KEY was not found. "
        "Add it to your .env file."
    )

client = Groq(
    api_key=api_key
)


# ============================================================
# BASIC STRING NORMALIZATION
# ============================================================

def normalize_string(value):
    """
    Safely normalize a string.

    Example:
        "  Orthopedic   Surgery "
        ->
        "orthopedic surgery"

    This is only formatting normalization.
    It does NOT perform semantic mapping.
    """

    if value is None:
        return None

    if not isinstance(value, str):
        return value

    return " ".join(
        value.strip().lower().split()
    )


# ============================================================
# CODE NORMALIZATION
# ============================================================

def normalize_code(value):
    """
    Normalize ICD-10 / CPT / HCPCS codes.

    Codes are treated as authoritative identifiers.
    """

    if value is None:
        return None

    return str(value).strip().upper()


# ============================================================
# LIST NORMALIZATION
# ============================================================

def normalize_string_list(values):
    """
    Normalize a list of strings without changing meaning.
    """

    if values is None:
        return []

    if not isinstance(values, list):
        values = [values]

    normalized = []

    for value in values:

        if value is None:
            continue

        if isinstance(value, str):

            value = normalize_string(value)

            if value:
                normalized.append(value)

        else:

            normalized.append(value)

    return normalized


# ============================================================
# BASIC PATIENT NORMALIZATION
# ============================================================

def basic_normalize_patient(patient):
    """
    Perform ONLY safe, policy-independent normalization.

    This function should run BEFORE policy matching.

    It must NOT attempt to convert things such as:

        "orthopedic surgery"
            ->
        "Orthopedics"

    because that requires knowledge of the applicable policy.

    That semantic normalization happens later inside
    normalize_patient(patient, policy).
    """

    if patient is None:
        return {}

    normalized = deepcopy(patient)


    # --------------------------------------------------------
    # Simple string fields
    # --------------------------------------------------------

    string_fields = [
        "patient_id",
        "patient_name",
        "gender",
        "payer",
        "diagnosis",
        "severity",
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


    # --------------------------------------------------------
    # Authoritative codes
    # --------------------------------------------------------

    normalized["icd10_code"] = normalize_code(
        normalized.get("icd10_code")
    )

    normalized["cpt_hcpcs_code"] = normalize_code(
        normalized.get("cpt_hcpcs_code")
    )


    # --------------------------------------------------------
    # Previous treatment
    # --------------------------------------------------------

    if "previous_treatment" in normalized:

        value = normalized["previous_treatment"]

        if isinstance(value, list):

            normalized["previous_treatment"] = (
                normalize_treatment_list(value)
            )

        elif isinstance(value, str):

            normalized["previous_treatment"] = [
                {
                    "treatment": normalize_string(value),
                    "duration_days": None
                }
            ]


    # --------------------------------------------------------
    # Previous procedure
    # --------------------------------------------------------

    if "previous_procedure" in normalized:

        value = normalized["previous_procedure"]

        if value is None:

            normalized["previous_procedure"] = []

        elif isinstance(value, list):

            normalized["previous_procedure"] = (
                normalize_string_list(value)
            )

        elif isinstance(value, str):

            normalized["previous_procedure"] = [
                normalize_string(value)
            ]


    # --------------------------------------------------------
    # Documentation
    # --------------------------------------------------------

    if "documentation" in normalized:

        if not isinstance(
            normalized["documentation"],
            dict
        ):

            normalized["documentation"] = {}


    # --------------------------------------------------------
    # Clinical information
    # --------------------------------------------------------

    if "clinical_information" in normalized:

        if not isinstance(
            normalized["clinical_information"],
            dict
        ):

            normalized["clinical_information"] = {}


    return normalized


# ============================================================
# TREATMENT NORMALIZATION
# ============================================================

def normalize_treatment_list(treatments):
    """
    Normalize previous-treatment structures.

    Supports both:

        ["Medication", "Physical Therapy"]

    and:

        [
            {
                "treatment": "Medication",
                "duration_days": 35
            }
        ]
    """

    normalized = []

    if not isinstance(treatments, list):
        return normalized

    for item in treatments:

        # ----------------------------------------------------
        # Dictionary representation
        # ----------------------------------------------------

        if isinstance(item, dict):

            treatment = item.get(
                "treatment",
                item.get("name")
            )

            duration = item.get(
                "duration_days"
            )

            if isinstance(
                duration,
                str
            ):

                try:
                    duration = int(
                        duration
                    )
                except (
                    TypeError,
                    ValueError
                ):
                    duration = None

            normalized.append(
                {
                    "treatment": normalize_string(
                        treatment
                    ),
                    "duration_days": duration
                }
            )

        # ----------------------------------------------------
        # Simple string representation
        # ----------------------------------------------------

        elif isinstance(item, str):

            normalized.append(
                {
                    "treatment": normalize_string(
                        item
                    ),
                    "duration_days": None
                }
            )

    return normalized


# ============================================================
# POLICY VOCABULARY
# ============================================================

def build_policy_vocabulary(policy):
    """
    Extract the policy's canonical vocabulary.

    The LLM receives this vocabulary so that it can map
    equivalent patient terminology to the exact values
    expected by the rule engine.
    """

    if not policy:
        return {}

    return {

        "payer": policy.get(
            "payer"
        ),

        "service_name": policy.get(
            "service_name"
        ),

        "cpt_hcpcs_codes": policy.get(
            "cpt_hcpcs_codes",
            []
        ),

        "covered_diagnoses": policy.get(
            "covered_diagnoses",
            []
        ),

        "icd10_codes": policy.get(
            "icd10_codes",
            []
        ),

        "severity_levels": (
            policy.get(
                "severity_requirement",
                {}
            ).get(
                "allowed_levels",
                []
            )
        ),

        "acceptable_treatments": (
            policy.get(
                "previous_treatment_requirement",
                {}
            ).get(
                "acceptable_treatments",
                []
            )
        ),

        "provider_specialties": policy.get(
            "provider_specialty_requirement",
            []
        ),

        "facility_types": policy.get(
            "facility_type_requirement",
            []
        ),

        "documentation_requirements": policy.get(
            "documentation_requirement",
            []
        )
    }


# ============================================================
# POLICY-AWARE NORMALIZATION
# ============================================================

def normalize_patient(patient, policy=None):
    """
    Normalize patient information.

    When a policy is supplied, the LLM uses that policy's
    vocabulary to canonicalize equivalent terminology.

    Example:

        Patient:
            "orthopedic surgery"

        Policy:
            ["Orthopedics", "Sports Medicine"]

        Result:

            "Orthopedics"

    ONLY if the terminology is genuinely equivalent.

    The LLM is NOT allowed to:
        - change ICD-10 codes
        - change CPT/HCPCS codes
        - invent clinical facts
        - invent documentation
        - invent severity
        - invent treatment duration
        - make the authorization decision
    """

    # --------------------------------------------------------
    # First perform safe normalization
    # --------------------------------------------------------

    patient = basic_normalize_patient(
        patient
    )

    # --------------------------------------------------------
    # No policy = no semantic normalization
    # --------------------------------------------------------

    if policy is None:
        return patient


    # ========================================================
    # POLICY VOCABULARY
    # ========================================================

    policy_vocabulary = (
        build_policy_vocabulary(
            policy
        )
    )


    # ========================================================
    # LLM PROMPT
    # ========================================================

    prompt = f"""
You are a medical prior-authorization data normalization
system.

Your task is to convert extracted patient information into
a canonical structure that can be evaluated deterministically
against an insurance policy.

You have:

1. PATIENT INFORMATION extracted from a medical document.
2. THE APPLICABLE POLICY.

Your job is ONLY normalization.

You are NOT the decision engine.

You must NOT decide APPROVED, DENIED, or MANUAL REVIEW.

============================================================
CORE RULE
============================================================

Never change a clinical fact merely to make the patient
satisfy the policy.

You may normalize terminology when two expressions have
the same clinical meaning.

For example:

Patient:
    "orthopedic surgery"

Policy vocabulary:
    "Orthopedics"

This can be normalized to:

    "Orthopedics"

because it may represent the same provider specialty.

But:

Patient:
    "Cardiology"

Policy:
    "Orthopedics"

must remain:

    "Cardiology"

Do NOT force it into "Orthopedics".

============================================================
AUTHORITATIVE CODES
============================================================

ICD-10 and CPT/HCPCS codes are authoritative.

NEVER modify them semantically.

If the patient has:

    M25.561

return:

    M25.561

If the patient has:

    73721

return:

    73721

Do not replace a code with a diagnosis name.

============================================================
DIAGNOSIS
============================================================

The ICD-10 code is the primary identifier.

Do not change the ICD-10 code.

The diagnosis text may be normalized for readability,
but it must remain clinically faithful.

============================================================
SEVERITY
============================================================

Only assign a policy severity such as:

    Moderate
    Severe

when the patient documentation explicitly states that
severity or provides sufficiently direct evidence.

For example:

    "Pain score 7/10 with moderate functional limitation"

may support:

    "Moderate"

But do NOT invent severity if the document contains
insufficient evidence.

If severity cannot safely be established:

    severity = null

Preserve supporting evidence whenever possible.

============================================================
PREVIOUS TREATMENT
============================================================

Preserve treatment names and durations.

Example:

    Ibuprofen 35 days

should become:

{{
    "treatment": "Medication",
    "duration_days": 35
}}

Example:

    Physical Therapy 6 weeks

should become approximately:

{{
    "treatment": "Physical Therapy",
    "duration_days": 42
}}

Only convert to a policy treatment category when the
meaning is equivalent.

Do not invent duration.

============================================================
PROVIDER SPECIALTY
============================================================

Map the provider specialty to a policy vocabulary item
ONLY when clinically equivalent.

Example:

    "Orthopedic Surgery"
    ->
    "Orthopedics"

when the policy contains "Orthopedics".

Do not change unrelated specialties.

============================================================
FACILITY
============================================================

Map equivalent facility terminology to the policy vocabulary.

Example:

    "Diagnostic Imaging Center"
    ->
    "Imaging Center"

if these clearly represent the same facility type.

Do not invent a facility type.

============================================================
DOCUMENTATION
============================================================

The patient document may contain information corresponding
to individual policy documentation requirements.

Evaluate each policy documentation requirement independently.

For example, if the policy requires:

    Clinical notes
    Physical examination
    Previous treatment history
    Relevant X-ray report

and the patient document contains all four, represent them
individually.

Do NOT simply set documentation_complete = true without
preserving the individual evidence.

Use a structure similar to:

"documentation": {{
    "Clinical notes": true,
    "Physical examination": true,
    "Previous treatment history": true,
    "Relevant X-ray report": true
}}

Only mark an item true when the document contains evidence
for it.

============================================================
FUNCTIONAL IMPAIRMENT
============================================================

If the policy requires functional impairment, preserve
explicit evidence such as:

    difficulty walking
    difficulty climbing stairs
    difficulty standing
    difficulty performing work duties

Do not invent functional impairment.

============================================================
QUANTITY
============================================================

Preserve the requested quantity.

Example:

    Quantity: 1 Study

should become:

    quantity = 1

Do not change the quantity.

============================================================
FREQUENCY
============================================================

Preserve frequency information if present.

Do not invent frequency if it is absent.

============================================================
OUTPUT
============================================================

Return ONLY valid JSON.

Use the same patient structure supplied in PATIENT INFORMATION.

Do not add explanatory text.

============================================================
PATIENT INFORMATION
============================================================

{json.dumps(patient, indent=2)}

============================================================
APPLICABLE POLICY
============================================================

{json.dumps(policy, indent=2)}

============================================================
POLICY CANONICAL VOCABULARY
============================================================

{json.dumps(policy_vocabulary, indent=2)}
"""


    # ============================================================
    # GROQ CALL WITH SAFE FALLBACK
    # ============================================================

    try:
        try:
            response = client.chat.completions.create(
                model="openai/gpt-oss-120b",
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You normalize medical authorization "
                            "data without changing clinical facts. "
                            "Return only valid JSON."
                        )
                    },
                    {
                        "role": "user",
                        "content": prompt + "\n\nRespond with a valid JSON object only."
                    }
                ],
                temperature=0,
                response_format={
                    "type": "json_object"
                }
            )
            content = response.choices[0].message.content
        except Exception:
            response = client.chat.completions.create(
                model="openai/gpt-oss-120b",
                messages=[
                    {
                        "role": "system",
                        "content": "You normalize medical authorization data. Return pure valid JSON only."
                    },
                    {
                        "role": "user",
                        "content": prompt + "\n\nReturn pure raw JSON only with no conversational text."
                    }
                ],
                temperature=0
            )
            content = response.choices[0].message.content

        if not content:
            return basic_normalize_patient(patient)

        normalized = json.loads(content)
        if not isinstance(normalized, dict):
            return basic_normalize_patient(patient)
    except Exception:
        # Safe fallback: Missing required evidence remains UNKNOWN -> MANUAL REVIEW
        return basic_normalize_patient(patient)


    # ========================================================
    # SAFETY: RESTORE AUTHORITATIVE IDENTIFIERS
    # ========================================================
    #
    # The LLM NEVER gets the final authority over codes.
    #
    # ========================================================

    normalized["icd10_code"] = (
        normalize_code(
            patient.get(
                "icd10_code"
            )
        )
    )

    normalized["cpt_hcpcs_code"] = (
        normalize_code(
            patient.get(
                "cpt_hcpcs_code"
            )
        )
    )

    normalized["patient_id"] = (
        patient.get(
            "patient_id"
        )
    )


    # ========================================================
    # SAFETY: RESTORE BASIC IDENTIFIERS
    # ========================================================

    if not normalized.get(
        "patient_name"
    ):

        normalized["patient_name"] = (
            patient.get(
                "patient_name"
            )
        )

    if normalized.get(
        "age"
    ) is None:

        normalized["age"] = (
            patient.get(
                "age"
            )
        )

    if not normalized.get(
        "gender"
    ):

        normalized["gender"] = (
            patient.get(
                "gender"
            )
        )

    if not normalized.get(
        "payer"
    ):

        normalized["payer"] = (
            patient.get(
                "payer"
            )
        )


    # ========================================================
    # ENSURE REQUEST FIELDS
    # ========================================================

    if not normalized.get(
        "requested_service"
    ):

        normalized["requested_service"] = (
            patient.get(
                "requested_service"
            )
        )


    # ========================================================
    # ENSURE PREVIOUS TREATMENT STRUCTURE
    # ========================================================

    if not isinstance(
        normalized.get(
            "previous_treatment"
        ),
        list
    ):

        normalized["previous_treatment"] = (
            patient.get(
                "previous_treatment",
                []
            )
        )


    # Normalize treatment list again
    normalized["previous_treatment"] = (
        normalize_treatment_list(
            normalized[
                "previous_treatment"
            ]
        )
    )


    # ========================================================
    # ENSURE PREVIOUS PROCEDURE STRUCTURE
    # ========================================================

    if not isinstance(
        normalized.get(
            "previous_procedure"
        ),
        list
    ):

        normalized["previous_procedure"] = (
            patient.get(
                "previous_procedure",
                []
            )
        )


    # ========================================================
    # ENSURE DOCUMENTATION STRUCTURE
    # ========================================================

    if not isinstance(
        normalized.get(
            "documentation"
        ),
        dict
    ):

        normalized["documentation"] = (
            patient.get(
                "documentation",
                {}
            )
        )


    # ========================================================
    # ENSURE CLINICAL INFORMATION
    # ========================================================

    if not isinstance(
        normalized.get(
            "clinical_information"
        ),
        dict
    ):

        normalized["clinical_information"] = (
            patient.get(
                "clinical_information",
                {}
            )
        )


    # ========================================================
    # PRESERVE DOCUMENTATION COMPLETENESS
    # ========================================================

    if (
        "documentation_complete"
        not in normalized
    ):

        normalized[
            "documentation_complete"
        ] = patient.get(
            "documentation_complete"
        )


    # ========================================================
    # PRESERVE QUANTITY
    # ========================================================

    if normalized.get(
        "quantity"
    ) is None:

        normalized["quantity"] = (
            patient.get(
                "quantity"
            )
        )


    # ========================================================
    # PRESERVE FREQUENCY
    # ========================================================

    if normalized.get(
        "frequency"
    ) is None:

        normalized["frequency"] = (
            patient.get(
                "frequency"
            )
        )


    # ========================================================
    # FINAL CODE NORMALIZATION
    # ========================================================

    normalized["icd10_code"] = (
        normalize_code(
            normalized.get(
                "icd10_code"
            )
        )
    )

    normalized["cpt_hcpcs_code"] = (
        normalize_code(
            normalized.get(
                "cpt_hcpcs_code"
            )
        )
    )


    if patient.get("_document_hash"):
        normalized["_document_hash"] = patient.get("_document_hash")

    # ========================================================
    # RETURN
    # ========================================================

    return normalized
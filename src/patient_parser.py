import json
import re
import os
from typing import Any, Dict, List, Optional

from groq import Groq
from dotenv import load_dotenv

load_dotenv()

# ============================================================
# PATIENT SCHEMA
# ============================================================

PATIENT_SCHEMA = {
    "patient_id": None,
    "patient_name": None,
    "age": None,
    "gender": None,
    "payer": None,

    "diagnosis": None,
    "icd10_code": None,

    "severity": None,
    "severity_evidence": [],

    "previous_treatment": [],
    "previous_procedure": [],

    "requested_service": None,
    "cpt_hcpcs_code": None,

    "quantity": None,
    "frequency": None,

    "provider_specialty": None,
    "facility_type": None,

    "documentation": {},

    "clinical_information": {}
}


# ============================================================
# LLM PROMPT
# ============================================================

PATIENT_EXTRACTION_PROMPT = """
You are a medical document information extraction system.

Your task is ONLY to extract facts from the supplied clinical
document.

You must NOT make a prior authorization decision.

You must NOT decide whether the patient is approved or denied.

You must NOT invent information.

You must preserve information that is explicitly supported by
the document.

Return ONLY valid JSON.

IMPORTANT:

DO NOT create a field called:

"documentation_complete"

The LLM must NEVER decide whether documentation is complete.

Instead, extract individual documentation items.

For example:

"documentation": {
    "Clinical notes": true,
    "Physical examination": true,
    "Previous treatment history": true,
    "Relevant X-ray report": true
}

The rule engine will later determine whether all documentation
required by the applicable policy is present.

------------------------------------------------------------
PATIENT STRUCTURE
------------------------------------------------------------

Return exactly this structure:

{
    "patient_id": null,
    "patient_name": null,
    "age": null,
    "gender": null,
    "payer": null,

    "diagnosis": null,
    "icd10_code": null,

    "severity": null,
    "severity_evidence": [],

    "previous_treatment": [],
    "previous_procedure": [],

    "requested_service": null,
    "cpt_hcpcs_code": null,

    "quantity": null,
    "frequency": null,

    "provider_specialty": null,
    "facility_type": null,

    "documentation": {},

    "clinical_information": {}
}

------------------------------------------------------------
FIELD RULES
------------------------------------------------------------

patient_id:
Extract MRN, patient ID, or equivalent identifier.

patient_name:
Extract the patient's full name.

age:
Extract numerical age if explicitly available.
If DOB is available but age is not explicitly stated,
calculate age only if the document provides enough
information.

gender:
Extract the documented gender.

payer:
Extract the insurance/payer name.

diagnosis:
Extract the diagnosis text.

icd10_code:
Extract the ICD-10 code exactly as documented.

severity:
Determine severity ONLY from documented clinical evidence.

Possible values:
- Mild
- Moderate
- Severe
- null

Do not invent severity.

severity_evidence:
List the clinical evidence supporting the severity.

Examples:
- "Pain score 7/10"
- "Moderate tenderness"
- "Severe functional limitation"

previous_treatment:
Every treatment must be represented as an object.

Example:

[
    {
        "treatment": "Medication",
        "specific_treatment": "Ibuprofen",
        "duration_days": 35
    },
    {
        "treatment": "Physical Therapy",
        "specific_treatment": "Physical Therapy",
        "duration_days": 42
    }
]

Convert weeks/months to days when the duration is explicitly
documented.

Examples:

6 weeks -> 42 days
5 weeks -> 35 days
30 days -> 30 days

Do NOT guess durations.

If a treatment is documented but duration is unknown:

{
    "treatment": "Medication",
    "specific_treatment": "Ibuprofen",
    "duration_days": null
}

previous_procedure:
List previous procedures separately from treatments.

Example:

[
    {
        "procedure": "Cortisone injection",
        "date": null
    }
]

If there are no previous procedures:

[]

requested_service:
Extract the requested service.

cpt_hcpcs_code:
Extract the CPT or HCPCS code.

quantity:
Extract requested quantity.

frequency:
Extract frequency if explicitly stated.

provider_specialty:
Extract the provider specialty.

Examples:
- Orthopedics
- Cardiology
- Oncology

Do NOT unnecessarily convert the provider specialty into a
policy decision.

facility_type:
Extract the facility type.

Examples:
- Hospital
- Imaging Center
- Outpatient Diagnostic Center

documentation:

Represent documentation as individual boolean facts.

The following are examples:

{
    "Clinical notes": true,
    "Physical examination": true,
    "Previous treatment history": true,
    "Relevant X-ray report": true
}

Only mark a documentation item true when the document contains
evidence of that item.

If there is no evidence, either omit the item or set it to false.

clinical_information:

Store supporting clinical facts that may be useful for policy
evaluation.

For example:

{
    "functional_impairment": true,
    "functional_impairment_evidence": [
        "Difficulty walking",
        "Difficulty climbing stairs"
    ],
    "contradictory_information": false,
    "history_of_present_illness": "...",
    "physical_examination": [
        "Moderate tenderness",
        "Mild swelling"
    ],
    "xray": {
        "performed": true,
        "findings": [
            "No fracture or dislocation"
        ]
    }
}

------------------------------------------------------------
IMPORTANT
------------------------------------------------------------

Do NOT create:

"documentation_complete"

Do NOT create:

"approved"

Do NOT create:

"denied"

Do NOT create:

"manual_review"

Do NOT create:

"policy_decision"

The rule engine is responsible for all policy decisions.
"""


# ============================================================
# HELPERS
# ============================================================

def _extract_json(text: str) -> Dict[str, Any]:
    """
    Extract a JSON object from an LLM response.
    """

    if not text:
        raise ValueError("LLM returned empty response.")

    text = text.strip()

    # Remove markdown fences if present
    text = re.sub(
        r"^```json\s*",
        "",
        text,
        flags=re.IGNORECASE
    )

    text = re.sub(
        r"^```\s*",
        "",
        text
    )

    text = re.sub(
        r"\s*```$",
        "",
        text
    )

    text = text.strip()

    try:
        result = json.loads(text)

        if not isinstance(result, dict):
            raise ValueError(
                "LLM response is not a JSON object."
            )

        return result

    except json.JSONDecodeError:

        # Try finding the first JSON object
        match = re.search(
            r"\{.*\}",
            text,
            flags=re.DOTALL
        )

        if not match:
            raise ValueError(
                "Could not find valid JSON in LLM response."
            )

        try:
            result = json.loads(
                match.group(0)
            )

        except json.JSONDecodeError as exc:

            raise ValueError(
                f"Invalid JSON returned by LLM: {exc}"
            )

        if not isinstance(result, dict):
            raise ValueError(
                "Extracted JSON is not an object."
            )

        return result


def _safe_int(value):
    """
    Convert a value to int where possible.
    """

    if value is None:
        return None

    if isinstance(value, bool):
        return None

    try:
        return int(float(value))
    except (
        TypeError,
        ValueError
    ):
        return None


def _safe_float(value):
    """
    Convert a value to float where possible.
    """

    if value is None:
        return None

    if isinstance(value, bool):
        return None

    try:
        return float(value)
    except (
        TypeError,
        ValueError
    ):
        return None


def _clean_string(value):
    """
    Safely clean a string field.
    """

    if value is None:
        return None

    if not isinstance(value, str):
        value = str(value)

    value = value.strip()

    return value if value else None


def _normalize_documentation(
    documentation
) -> Dict[str, bool]:
    """
    Normalize documentation keys and values.

    This does NOT determine completeness.
    It only cleans the extracted facts.
    """

    if not isinstance(
        documentation,
        dict
    ):
        return {}

    result = {}

    for key, value in documentation.items():

        if key is None:
            continue

        clean_key = str(key).strip()

        if not clean_key:
            continue

        if isinstance(value, bool):
            result[clean_key] = value

        elif isinstance(value, str):

            result[clean_key] = (
                value.strip().lower()
                in {
                    "true",
                    "yes",
                    "present",
                    "available",
                    "documented"
                }
            )

        else:
            result[clean_key] = bool(value)

    return result


def _normalize_treatments(
    treatments
) -> List[Dict[str, Any]]:
    """
    Ensure previous_treatment has the expected structure.
    """

    if not isinstance(
        treatments,
        list
    ):
        return []

    result = []

    for item in treatments:

        if isinstance(
            item,
            str
        ):

            result.append(
                {
                    "treatment": item.strip(),
                    "specific_treatment": item.strip(),
                    "duration_days": None
                }
            )

            continue

        if not isinstance(
            item,
            dict
        ):
            continue

        treatment = _clean_string(
            item.get("treatment")
        )

        specific = _clean_string(
            item.get("specific_treatment")
        )

        duration = _safe_float(
            item.get("duration_days")
        )

        if duration is not None:

            if duration.is_integer():
                duration = int(duration)

        if treatment:

            result.append(
                {
                    "treatment": treatment,
                    "specific_treatment": (
                        specific or treatment
                    ),
                    "duration_days": duration
                }
            )

    return result


def _normalize_procedures(
    procedures
) -> List[Dict[str, Any]]:
    """
    Normalize previous procedures.
    """

    if not isinstance(
        procedures,
        list
    ):
        return []

    result = []

    for item in procedures:

        if isinstance(
            item,
            str
        ):

            result.append(
                {
                    "procedure": item.strip(),
                    "date": None
                }
            )

            continue

        if not isinstance(
            item,
            dict
        ):
            continue

        procedure = _clean_string(
            item.get("procedure")
        )

        date = _clean_string(
            item.get("date")
        )

        if procedure:

            result.append(
                {
                    "procedure": procedure,
                    "date": date
                }
            )

    return result


# ============================================================
# PATIENT CLEANING
# ============================================================

def clean_patient(
    patient: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Clean and validate the extracted patient structure.

    IMPORTANT:
    This function does NOT make policy decisions.
    """

    result = dict(PATIENT_SCHEMA)

    if not isinstance(
        patient,
        dict
    ):
        patient = {}

    # --------------------------------------------------------
    # Simple fields
    # --------------------------------------------------------

    result["patient_id"] = _clean_string(
        patient.get("patient_id")
    )

    result["patient_name"] = _clean_string(
        patient.get("patient_name")
    )

    result["age"] = _safe_int(
        patient.get("age")
    )

    result["gender"] = _clean_string(
        patient.get("gender")
    )

    result["payer"] = _clean_string(
        patient.get("payer")
    )

    result["diagnosis"] = _clean_string(
        patient.get("diagnosis")
    )

    result["icd10_code"] = _clean_string(
        patient.get("icd10_code")
    )

    result["severity"] = _clean_string(
        patient.get("severity")
    )

    severity_evidence = patient.get(
        "severity_evidence",
        []
    )

    if isinstance(
        severity_evidence,
        list
    ):
        result["severity_evidence"] = [
            str(item).strip()
            for item in severity_evidence
            if str(item).strip()
        ]

    result["requested_service"] = _clean_string(
        patient.get("requested_service")
    )

    result["cpt_hcpcs_code"] = _clean_string(
        patient.get("cpt_hcpcs_code")
    )

    result["quantity"] = _safe_float(
        patient.get("quantity")
    )

    if (
        result["quantity"] is not None
        and result["quantity"].is_integer()
    ):
        result["quantity"] = int(
            result["quantity"]
        )

    result["frequency"] = _clean_string(
        patient.get("frequency")
    )

    result["provider_specialty"] = _clean_string(
        patient.get("provider_specialty")
    )

    result["facility_type"] = _clean_string(
        patient.get("facility_type")
    )

    # --------------------------------------------------------
    # Structured fields
    # --------------------------------------------------------

    result["previous_treatment"] = (
        _normalize_treatments(
            patient.get(
                "previous_treatment",
                []
            )
        )
    )

    result["previous_procedure"] = (
        _normalize_procedures(
            patient.get(
                "previous_procedure",
                []
            )
        )
    )

    result["documentation"] = (
        _normalize_documentation(
            patient.get(
                "documentation",
                {}
            )
        )
    )

    clinical_information = patient.get(
        "clinical_information",
        {}
    )

    if not isinstance(
        clinical_information,
        dict
    ):
        clinical_information = {}

    result["clinical_information"] = (
        clinical_information
    )

    # --------------------------------------------------------
    # CRITICAL:
    #
    # Never allow documentation_complete through.
    # --------------------------------------------------------

    result.pop(
        "documentation_complete",
        None
    )

    # Also remove accidental decision fields.
    result.pop(
        "approved",
        None
    )

    result.pop(
        "denied",
        None
    )

    result.pop(
        "manual_review",
        None
    )

    result.pop(
        "policy_decision",
        None
    )

    return result


# ============================================================
# MAIN PARSER
# ============================================================

def parse_patient(
    text: str,
    api_key: Optional[str] = None,
    model: str = "llama-3.3-70b-versatile"
):
    if not text or not text.strip():
        raise ValueError(
            "Patient document text is empty."
        )

    # --------------------------------------------------------
    # Load API key from .env if it wasn't explicitly supplied
    # --------------------------------------------------------

    if not api_key:
        api_key = os.getenv("GROQ_API_KEY")

    if not api_key:
        raise ValueError(
            "GROQ_API_KEY was not found. "
            "Check your .env file."
        )

    client = Groq(
        api_key=api_key
    )
    response = client.chat.completions.create(
        model=model,
        temperature=0,
        messages=[
            {
                "role": "system",
                "content": PATIENT_EXTRACTION_PROMPT
            },
            {
                "role": "user",
                "content": (
                    "Extract the patient information "
                    "from the following document:\n\n"
                    + text
                )
            }
        ]
    )

    raw_content = response.choices[0].message.content

    extracted = _extract_json(
        raw_content
    )

    patient = clean_patient(
        extracted
    )

    return patient
# ============================================================
# BACKWARD-COMPATIBLE PATIENT VALIDATION
# ============================================================

def validate_patient(patient):
    """
    Validate the basic structure of extracted patient data.

    IMPORTANT:
    This function only checks whether the extracted patient
    object has the basic structure needed by the application.

    It does NOT validate policy-specific requirements.

    Policy-specific checks such as:
        - allowed ICD-10
        - severity
        - previous treatment duration
        - provider specialty
        - documentation requirements
        - quantity limits

    are handled by rule_engine.py after the policy is identified.
    """

    errors = []

    if not isinstance(patient, dict):
        return {
            "valid": False,
            "errors": [
                "Patient data must be a dictionary."
            ]
        }

    # --------------------------------------------------------
    # Basic patient fields
    # --------------------------------------------------------

    if not patient.get("patient_id"):
        errors.append(
            "Patient ID is missing."
        )

    if not patient.get("patient_name"):
        errors.append(
            "Patient name is missing."
        )

    if patient.get("age") is None:
        errors.append(
            "Patient age is missing."
        )

    if not patient.get("gender"):
        errors.append(
            "Patient gender is missing."
        )

    if not patient.get("payer"):
        errors.append(
            "Payer/insurance information is missing."
        )

    # --------------------------------------------------------
    # Requested service
    # --------------------------------------------------------

    if not patient.get("requested_service"):
        errors.append(
            "Requested service is missing."
        )

    if not patient.get("cpt_hcpcs_code"):
        errors.append(
            "CPT/HCPCS code is missing."
        )

    # --------------------------------------------------------
    # Diagnosis
    # --------------------------------------------------------

    if not patient.get("diagnosis"):
        errors.append(
            "Diagnosis is missing."
        )

    if not patient.get("icd10_code"):
        errors.append(
            "ICD-10 code is missing."
        )

    # --------------------------------------------------------
    # Structured fields
    # --------------------------------------------------------

    if not isinstance(
        patient.get("previous_treatment", []),
        list
    ):
        errors.append(
            "Previous treatment must be a list."
        )

    if not isinstance(
        patient.get("previous_procedure", []),
        list
    ):
        errors.append(
            "Previous procedure must be a list."
        )

    if not isinstance(
        patient.get("documentation", {}),
        dict
    ):
        errors.append(
            "Documentation must be a dictionary."
        )

    if not isinstance(
        patient.get("severity_evidence", []),
        list
    ):
        errors.append(
            "Severity evidence must be a list."
        )

    if not isinstance(
        patient.get("clinical_information", {}),
        dict
    ):
        errors.append(
            "Clinical information must be a dictionary."
        )

    # --------------------------------------------------------
    # IMPORTANT:
    #
    # We intentionally DO NOT require:
    #
    # severity
    # provider_specialty
    # facility_type
    # documentation
    # previous_treatment
    #
    # because these are policy-specific.
    #
    # The rule engine decides whether they are required.
    # --------------------------------------------------------

    return {
        "valid": len(errors) == 0,
        "errors": errors
    }
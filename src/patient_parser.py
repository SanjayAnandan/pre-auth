import os
import json

from groq import Groq
from dotenv import load_dotenv


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
    "previous_treatment": None,
    "previous_procedure": None,
    "requested_service": None,
    "cpt_hcpcs_code": None,
    "quantity": None,
    "frequency": None,
    "documentation_complete": None,
    "provider_specialty": None,
    "facility_type": None
}


# ============================================================
# LLM EXTRACTION
# ============================================================

def parse_patient(text):

    if not text or not text.strip():

        raise ValueError(
            "No text was extracted from the PDF."
        )

    prompt = f"""
You are a medical document information extraction system.

Extract patient and authorization-request information
from the supplied medical document.

IMPORTANT RULES:

1. Extract ONLY information explicitly present in the document.
2. Do NOT invent or guess missing information.
3. If a field is not present, return null.
4. Different documents may use different labels for the
   same concept.
5. Understand synonyms and variations.

Examples:

"Payer / Insurance", "Insurance", "Health Plan",
"Coverage Provider" -> payer

"Patient ID", "MRN", "Medical Record Number" -> patient_id

"Requested Service", "Procedure Requested",
"Service Requested" -> requested_service

"CPT", "HCPCS", "Procedure Code" -> cpt_hcpcs_code

6. Preserve the actual meaning of the document.
7. Return ONLY valid JSON.
8. Do not add explanations outside the JSON.

Return exactly this structure:

{json.dumps(PATIENT_SCHEMA, indent=2)}

DOCUMENT:

{text}
"""

    response = client.chat.completions.create(

        model="llama-3.3-70b-versatile",

        messages=[
            {
                "role": "system",
                "content": (
                    "You are a precise medical "
                    "document extraction system."
                )
            },
            {
                "role": "user",
                "content": prompt
            }
        ],

        temperature=0,

        response_format={
            "type": "json_object"
        }
    )

    content = response.choices[0].message.content

    if not content:
        raise ValueError(
            "LLM returned an empty response."
        )

    try:

        patient = json.loads(content)

    except json.JSONDecodeError as e:

        raise ValueError(
            f"LLM returned invalid JSON: {e}"
        )


    # Make sure every expected field exists

    for field in PATIENT_SCHEMA:

        if field not in patient:

            patient[field] = None

    # ============================================================
    # TYPE NORMALIZATION
    # ============================================================

    # Quantity
    if patient.get("quantity") is not None:

        try:
            patient["quantity"] = int(
                patient["quantity"]
            )
        except (TypeError, ValueError):
            patient["quantity"] = None


    # Age
    if patient.get("age") is not None:

        try:
            patient["age"] = int(
                patient["age"]
            )
        except (TypeError, ValueError):
            patient["age"] = None


    # Documentation
    if isinstance(
        patient.get("documentation_complete"),
        str
    ):

        value = patient[
            "documentation_complete"
        ].strip().lower()

        if value in ["yes", "true"]:
            patient[
                "documentation_complete"
            ] = True

        elif value in ["no", "false"]:
            patient[
                "documentation_complete"
            ] = False

        else:
            patient[
                "documentation_complete"
            ] = None


    return patient


# ============================================================
# VALIDATION
# ============================================================

def validate_patient(patient):

    required_fields = [
        "patient_id",
        "payer",
        "diagnosis",
        "icd10_code",
        "requested_service",
        "cpt_hcpcs_code"
    ]

    missing_fields = []

    for field in required_fields:

        value = patient.get(field)

        if value is None:
            missing_fields.append(field)

        elif isinstance(value, str) and not value.strip():
            missing_fields.append(field)


    return {
        "valid": len(missing_fields) == 0,
        "missing_fields": missing_fields
    }
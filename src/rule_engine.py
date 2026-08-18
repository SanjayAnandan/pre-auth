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
    text = " ".join(text.split())
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
    except (TypeError, ValueError):
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
        "nsaid": "medication",
        "nsaids": "medication",
        "nsaid therapy": "medication",
        "analgesic": "medication",
        "ibuprofen": "medication",

        # Physical therapy
        "physical therapy": "physical therapy",
        "physiotherapy": "physical therapy",
        "pt": "physical therapy",

        # Activity modification
        "activity modification": "activity modification",
        "activity modifications": "activity modification",
        "modified activity": "activity modification",
        "home exercise": "activity modification",
        "exercise": "activity modification",
    }

    return aliases.get(text, text)


def canonical_provider_specialty(value) -> str:
    text = normalize(value)

    aliases = {
        "orthopedics": "orthopedics",
        "orthopedic": "orthopedics",
        "orthopedic surgery": "orthopedics",
        "orthopaedics": "orthopedics",
        "orthopaedic surgery": "orthopedics",

        "neurology": "neurology",
        "neurologist": "neurology",
        "neurosurgery": "neurosurgery",
        "neurosurgeon": "neurosurgery",

        "sports medicine": "sports medicine",
        "cardiology": "cardiology",
        "cardiologist": "cardiology",
        "oncology": "oncology",
        "oncologist": "oncology"
    }

    return aliases.get(text, text)


def canonical_facility_type(value) -> str:
    text = normalize(value)

    aliases = {
        "hospital": "hospital",
        "imaging center": "imaging center",
        "imaging centre": "imaging center",
        "outpatient diagnostic center": "outpatient diagnostic center",
        "outpatient diagnostic centre": "outpatient diagnostic center",
        "diagnostic imaging center": "imaging center"
    }

    return aliases.get(text, text)


# ============================================================
# DOCUMENTATION EVIDENCE MATCHING (FIX 1)
# ============================================================

def is_documentation_satisfied(required_doc: str, patient: Dict[str, Any]) -> bool:
    """
    Deterministically check whether clinical evidence satisfies a required documentation item.
    Matches equivalent clinical terminology and structured evidence without extra LLM calls.
    Requires actual documented evidence from submitted documents.
    """
    if not required_doc:
        return True

    doc_norm = normalize(required_doc)

    # 1. Direct check in patient["documentation"] dict
    documentation = patient.get("documentation") or {}
    if isinstance(documentation, dict):
        for k, v in documentation.items():
            if v is True and normalize(k) == doc_norm:
                return True
            if v and isinstance(v, str) and v.strip().lower() in {"true", "yes", "present", "available", "documented"}:
                if normalize(k) == doc_norm:
                    return True

    clinical_info = patient.get("clinical_information") or {}
    if not isinstance(clinical_info, dict):
        clinical_info = {}

    # Extract all text evidence in patient dict for fallback matching
    evidence_text_list = []
    if isinstance(patient.get("severity_evidence"), list):
        evidence_text_list.extend([str(item) for item in patient["severity_evidence"]])
    if isinstance(clinical_info.get("physical_examination"), list):
        evidence_text_list.extend([str(item) for item in clinical_info["physical_examination"]])
    elif isinstance(clinical_info.get("physical_examination"), str):
        evidence_text_list.append(clinical_info["physical_examination"])
    if isinstance(clinical_info.get("history_of_present_illness"), str):
        evidence_text_list.append(clinical_info["history_of_present_illness"])
    if isinstance(clinical_info.get("neurological_examination"), str):
        evidence_text_list.append(clinical_info["neurological_examination"])

    full_evidence_text = " ".join(evidence_text_list).lower()

    # 2. Concept-specific evidence matching

    # --- NEUROLOGICAL EXAMINATION ---
    if "neurological" in doc_norm:
        # Direct check in documentation dict for explicit key
        for k, v in documentation.items():
            if v is True and "neurological" in normalize(k):
                return True

        # Structured clinical_information for explicit exam / findings
        if clinical_info.get("neurological_examination") is True or (isinstance(clinical_info.get("neurological_examination"), (list, dict, str)) and clinical_info.get("neurological_examination")):
            return True
        if clinical_info.get("neurological_findings") is True or (isinstance(clinical_info.get("neurological_findings"), (list, dict, str)) and clinical_info.get("neurological_findings")):
            return True

        # Check specific actual neurological exam findings terms (NOT symptoms or diagnoses like radiculopathy/pain/radiating)
        actual_neuro_exam_findings = [
            "sensory reduction", "sensory loss", "diminished sensation", "intact sensation",
            "numbness", "tingling", "hypesthesia", "paresthesia",
            "motor strength", "motor weakness", "5/5", "4/5", "3/5", "dorsiflexion", "plantarflexion",
            "patellar reflex", "achilles reflex", "deep tendon reflex", "hyperreflexia", "hyporeflexia", "symmetric reflexes", "diminished reflex",
            "straight-leg raise", "straight leg raise", "slr", "positive slr", "negative slr"
        ]
        if any(term in full_evidence_text for term in actual_neuro_exam_findings):
            return True

        return False

    # --- RELEVANT IMAGING REPORT / X-RAY ---
    if any(term in doc_norm for term in ["imaging", "x ray", "xray", "mri", "ct", "radiology"]):
        # Direct check in documentation dict for explicit prior report keys
        for k, v in documentation.items():
            if v is True and any(term in normalize(k) for term in ["imaging", "x-ray", "xray", "radiology", "scan"]):
                norm_k = normalize(k)
                if "report" in norm_k or "x-ray" in norm_k or "xray" in norm_k or "prior" in norm_k or "lumbar spine x-ray" in norm_k:
                    return True

        # Structured clinical_information prior imaging object
        if clinical_info.get("xray") or clinical_info.get("xray_report") or clinical_info.get("prior_imaging") or clinical_info.get("imaging_findings") or clinical_info.get("lumbar_spine_xray"):
            return True

        # Check for actual prior imaging findings / report terms in text evidence
        actual_imaging_report_terms = [
            "x-ray report", "xray report", "lumbar spine x-ray", "lumbar x-ray",
            "prior mri report", "prior mri", "ct report", "radiology report",
            "x-ray findings", "xray findings", "imaging findings",
            "disc space narrowing", "spondylolisthesis", "plain radiograph", "radiograph"
        ]
        if any(term in full_evidence_text for term in actual_imaging_report_terms):
            return True

        return False

    # --- CLINICAL NOTES ---
    if "clinical notes" in doc_norm or "notes" in doc_norm:
        for k, v in documentation.items():
            if v is True and ("clinical" in normalize(k) or "notes" in normalize(k)):
                return True
        if patient.get("patient_id") or patient.get("diagnosis") or clinical_info:
            return True

    # --- PREVIOUS TREATMENT HISTORY ---
    if "treatment" in doc_norm or "history" in doc_norm:
        for k, v in documentation.items():
            if v is True and ("treatment" in normalize(k) or "history" in normalize(k)):
                return True
        prev_treatments = patient.get("previous_treatment")
        if isinstance(prev_treatments, list) and len(prev_treatments) > 0:
            return True

    # --- PHYSICAL EXAMINATION ---
    if "physical examination" in doc_norm or "examination" in doc_norm:
        for k, v in documentation.items():
            if v is True and ("physical" in normalize(k) or "examination" in normalize(k) or "exam" in normalize(k)):
                return True
        if clinical_info.get("physical_examination"):
            return True

    return False


# ============================================================
# CPT / HCPCS
# ============================================================

def check_cpt_hcpcs(
    patient: Dict[str, Any],
    policy: Dict[str, Any]
):
    patient_code = normalize(patient.get("cpt_hcpcs_code"))
    policy_codes = [normalize(code) for code in policy.get("cpt_hcpcs_codes", [])]

    if not patient_code:
        return {
            "criterion": "CPT/HCPCS",
            "status": "UNKNOWN",
            "reason": "CPT/HCPCS code is missing from request."
        }

    if patient_code in policy_codes:
        return {
            "criterion": "CPT/HCPCS",
            "status": "PASSED",
            "reason": f"CPT/HCPCS {patient_code} is covered by the policy."
        }

    return {
        "criterion": "CPT/HCPCS",
        "status": "FAILED",
        "reason": f"CPT/HCPCS {patient.get('cpt_hcpcs_code')} is not covered by policy {policy.get('policy_id')} (Covered codes: {', '.join(policy.get('cpt_hcpcs_codes', []))})."
    }


# ============================================================
# DIAGNOSIS
# ============================================================

def check_diagnosis(
    patient: Dict[str, Any],
    policy: Dict[str, Any]
):
    patient_code = normalize(patient.get("icd10_code"))
    diagnosis = normalize(patient.get("diagnosis"))
    policy_codes = [normalize(code) for code in policy.get("icd10_codes", [])]
    covered_diagnoses = [normalize(item) for item in policy.get("covered_diagnoses", [])]

    if not patient_code and not diagnosis:
        return {
            "criterion": "Diagnosis",
            "status": "UNKNOWN",
            "reason": "ICD-10 diagnosis code and diagnosis description are missing."
        }

    if (patient_code and patient_code in policy_codes) or (diagnosis and diagnosis in covered_diagnoses):
        return {
            "criterion": "Diagnosis",
            "status": "PASSED",
            "reason": f"Diagnosis '{patient.get('diagnosis') or patient_code}' (ICD-10: {patient.get('icd10_code')}) is covered by the policy."
        }

    return {
        "criterion": "Diagnosis",
        "status": "FAILED",
        "reason": f"Documented ICD-10 {patient.get('icd10_code')} ('{patient.get('diagnosis')}') is not covered by policy {policy.get('policy_id')}."
    }


# ============================================================
# AGE
# ============================================================

def check_age(
    patient: Dict[str, Any],
    policy: Dict[str, Any]
):
    requirement = policy.get("age_requirement")
    if not requirement or not requirement.get("required", False):
        return {
            "criterion": "Age",
            "status": "NOT_APPLICABLE",
            "reason": "No age requirement for policy."
        }

    age = to_number(patient.get("age"))
    if age is None:
        return {
            "criterion": "Age",
            "status": "UNKNOWN",
            "reason": "Patient age is missing from document."
        }

    minimum = to_number(requirement.get("minimum_age"))
    maximum = to_number(requirement.get("maximum_age"))

    if minimum is not None and age < minimum:
        return {
            "criterion": "Age",
            "status": "FAILED",
            "reason": f"Patient age {age:g} is below policy minimum age of {minimum:g}."
        }

    if maximum is not None and age > maximum:
        return {
            "criterion": "Age",
            "status": "FAILED",
            "reason": f"Patient age {age:g} exceeds policy maximum age of {maximum:g}."
        }

    return {
        "criterion": "Age",
        "status": "PASSED",
        "reason": f"Patient age {age:g} satisfies policy requirement ({minimum:g}–{maximum:g} years)."
    }


# ============================================================
# SEVERITY
# ============================================================

def check_severity(
    patient: Dict[str, Any],
    policy: Dict[str, Any]
):
    requirement = policy.get("severity_requirement")
    if not requirement or not requirement.get("required", False):
        return {
            "criterion": "Severity",
            "status": "NOT_APPLICABLE",
            "reason": "No severity requirement for policy."
        }

    severity = normalize(patient.get("severity"))
    allowed = [normalize(level) for level in requirement.get("allowed_levels", [])]

    if not severity:
        return {
            "criterion": "Severity",
            "status": "UNKNOWN",
            "reason": "Clinical severity is missing from document."
        }

    if severity not in allowed:
        return {
            "criterion": "Severity",
            "status": "FAILED",
            "reason": f"Severity '{patient.get('severity')}' does not satisfy required policy severity ({', '.join(requirement.get('allowed_levels', []))})."
        }

    if requirement.get("functional_impairment_required", False):
        clinical_info = patient.get("clinical_information") or {}
        if not isinstance(clinical_info, dict):
            clinical_info = {}
        functional = clinical_info.get("functional_impairment")
        if functional is not True:
            evidence = " ".join([str(x) for x in patient.get("severity_evidence", [])]).lower()
            if "functional" in evidence or "impairment" in evidence or "limitation" in evidence or "difficulty" in evidence:
                pass
            elif functional is False:
                return {
                    "criterion": "Severity",
                    "status": "FAILED",
                    "reason": "Functional impairment was documented as absent."
                }
            else:
                return {
                    "criterion": "Severity",
                    "status": "UNKNOWN",
                    "reason": "Required functional impairment documentation is missing."
                }

    return {
        "criterion": "Severity",
        "status": "PASSED",
        "reason": f"Severity '{patient.get('severity')}' satisfies policy requirement."
    }


# ============================================================
# PREVIOUS TREATMENT
# ============================================================

def check_previous_treatment(
    patient: Dict[str, Any],
    policy: Dict[str, Any]
):
    requirement = policy.get("previous_treatment_requirement")
    if not requirement or not requirement.get("required", False):
        return {
            "criterion": "Previous Treatment",
            "status": "NOT_APPLICABLE",
            "reason": "No previous treatment requirement for policy."
        }

    previous = patient.get("previous_treatment")
    if previous is None:
        return {
            "criterion": "Previous Treatment",
            "status": "UNKNOWN",
            "reason": "Previous treatment details not documented or unextracted."
        }

    if not isinstance(previous, list):
        return {
            "criterion": "Previous Treatment",
            "status": "UNKNOWN",
            "reason": "Previous treatment information has an invalid structure."
        }

    if not previous:
        return {
            "criterion": "Previous Treatment",
            "status": "UNKNOWN",
            "reason": "No conservative treatment history was documented."
        }

    acceptable = requirement.get("acceptable_treatments", [])
    minimum_duration = to_number(requirement.get("minimum_duration_days", 0)) or 0
    match_mode = normalize(requirement.get("match_mode", "ANY")).upper()

    if not acceptable:
        return {
            "criterion": "Previous Treatment",
            "status": "PASSED",
            "reason": "Previous treatment is documented and no specific treatment type is required."
        }

    acceptable_map = {canonical_treatment(t): t for t in acceptable}
    matched = []
    disqualified_by_duration = []

    for item in previous:
        if not isinstance(item, dict):
            continue
        treatment = item.get("treatment") or item.get("specific_treatment")
        duration = item.get("duration_days")
        if not treatment:
            continue
        canonical = canonical_treatment(treatment)
        if canonical not in acceptable_map:
            continue
        duration_value = to_number(duration)
        if duration_value is None:
            continue
        if duration_value >= minimum_duration:
            matched.append({
                "patient_treatment": treatment,
                "policy_treatment": acceptable_map[canonical],
                "duration_days": duration_value
            })
        else:
            disqualified_by_duration.append({
                "patient_treatment": treatment,
                "duration_days": duration_value
            })

    if match_mode == "ANY":
        if matched:
            res = matched[0]
            return {
                "criterion": "Previous Treatment",
                "status": "PASSED",
                "reason": f"Previous treatment '{res['patient_treatment']}' was documented for {res['duration_days']:g} days. Minimum required duration is {minimum_duration:g} days."
            }
        if disqualified_by_duration:
            disq = disqualified_by_duration[0]
            return {
                "criterion": "Previous Treatment",
                "status": "FAILED",
                "reason": f"Documented conservative treatment '{disq['patient_treatment']}' duration ({disq['duration_days']:g} days) is less than required minimum ({minimum_duration:g} days)."
            }
        patient_treatments_str = ", ".join([str(t.get('treatment') or t) for t in previous if isinstance(t, dict)])
        return {
            "criterion": "Previous Treatment",
            "status": "UNKNOWN",
            "reason": f"No acceptable conservative treatment ({', '.join(acceptable)}) with minimum duration ({minimum_duration:g} days) was documented."
        }

    if match_mode == "ALL":
        matched_types = {m["policy_treatment"] for m in matched}
        missing = [t for t in acceptable if t not in matched_types]
        if not missing:
            return {
                "criterion": "Previous Treatment",
                "status": "PASSED",
                "reason": "All required previous treatments satisfy policy requirements."
            }
        return {
            "criterion": "Previous Treatment",
            "status": "FAILED",
            "reason": f"The following required conservative treatments do not satisfy policy minimum duration ({minimum_duration:g} days): {', '.join(missing)}."
        }

    return {
        "criterion": "Previous Treatment",
        "status": "UNKNOWN",
        "reason": f"Unsupported treatment match mode: {match_mode}"
    }


# ============================================================
# PREVIOUS PROCEDURE
# ============================================================

def check_previous_procedure(
    patient: Dict[str, Any],
    policy: Dict[str, Any]
):
    requirement = policy.get("previous_procedure_requirement")
    if not requirement or not requirement.get("required", False):
        return {
            "criterion": "Previous Procedure",
            "status": "NOT_APPLICABLE",
            "reason": "No previous procedure requirement."
        }

    procedures = patient.get("previous_procedure")
    required_procs = requirement.get("procedures", [])

    if procedures is None:
        return {
            "criterion": "Previous Procedure",
            "status": "UNKNOWN",
            "reason": f"Required previous procedure ({', '.join(required_procs)}) details are missing from document."
        }

    if not procedures:
        return {
            "criterion": "Previous Procedure",
            "status": "UNKNOWN",
            "reason": f"Required previous procedure ({', '.join(required_procs)}) was not documented."
        }

    proc_names = [normalize(p.get("procedure") if isinstance(p, dict) else p) for p in procedures]
    matched = [req for req in required_procs if normalize(req) in proc_names or any(normalize(req) in p for p in proc_names)]

    if matched:
        return {
            "criterion": "Previous Procedure",
            "status": "PASSED",
            "reason": f"Required previous procedure ({', '.join(matched)}) is documented."
        }

    return {
        "criterion": "Previous Procedure",
        "status": "UNKNOWN",
        "reason": f"Required procedure ({', '.join(required_procs)}) was not found in submitted records."
    }


# ============================================================
# PROVIDER SPECIALTY
# ============================================================

def check_provider_specialty(
    patient: Dict[str, Any],
    policy: Dict[str, Any]
):
    required = policy.get("provider_specialty_requirement")
    if not required:
        return {
            "criterion": "Provider Specialty",
            "status": "NOT_APPLICABLE",
            "reason": "No provider specialty requirement."
        }

    patient_specialty = canonical_provider_specialty(patient.get("provider_specialty"))

    if not patient_specialty:
        return {
            "criterion": "Provider Specialty",
            "status": "UNKNOWN",
            "reason": "Provider specialty is missing from document."
        }

    allowed = {canonical_provider_specialty(item) for item in required}

    if patient_specialty in allowed:
        return {
            "criterion": "Provider Specialty",
            "status": "PASSED",
            "reason": f"Provider specialty '{patient.get('provider_specialty')}' is eligible."
        }

    return {
        "criterion": "Provider Specialty",
        "status": "FAILED",
        "reason": f"Provider specialty '{patient.get('provider_specialty')}' is not eligible (Eligible: {', '.join(required)})."
    }


# ============================================================
# FACILITY
# ============================================================

def check_facility(
    patient: Dict[str, Any],
    policy: Dict[str, Any]
):
    required = policy.get("facility_type_requirement")
    if not required:
        return {
            "criterion": "Facility",
            "status": "NOT_APPLICABLE",
            "reason": "No facility requirement."
        }

    patient_facility = canonical_facility_type(patient.get("facility_type"))

    if not patient_facility:
        return {
            "criterion": "Facility",
            "status": "UNKNOWN",
            "reason": "Facility type is missing from document."
        }

    allowed = {canonical_facility_type(item) for item in required}

    if patient_facility in allowed:
        return {
            "criterion": "Facility",
            "status": "PASSED",
            "reason": f"Facility '{patient.get('facility_type')}' is eligible."
        }

    return {
        "criterion": "Facility",
        "status": "FAILED",
        "reason": f"Facility '{patient.get('facility_type')}' is not eligible (Eligible: {', '.join(required)})."
    }


# ============================================================
# DOCUMENTATION
# ============================================================

def check_documentation(
    patient: Dict[str, Any],
    policy: Dict[str, Any]
):
    required_docs = policy.get("documentation_requirement", [])
    if not required_docs:
        return {
            "criterion": "Documentation",
            "status": "NOT_APPLICABLE",
            "reason": "No specific documentation requirements."
        }

    missing_docs = []
    satisfied_docs = []

    for required_doc in required_docs:
        if is_documentation_satisfied(required_doc, patient):
            satisfied_docs.append(required_doc)
        else:
            missing_docs.append(required_doc)

    if not missing_docs:
        return {
            "criterion": "Documentation",
            "status": "PASSED",
            "reason": f"All required policy documentation is present: {', '.join(required_docs)}."
        }

    return {
        "criterion": "Documentation",
        "status": "UNKNOWN",
        "reason": f"Required policy evidence was not available in submitted documents: {', '.join(missing_docs)}."
    }


# ============================================================
# QUANTITY
# ============================================================

def check_quantity(
    patient: Dict[str, Any],
    policy: Dict[str, Any]
):
    requirement = policy.get("quantity_limit")
    if not requirement:
        return {
            "criterion": "Quantity",
            "status": "NOT_APPLICABLE",
            "reason": "No quantity limit."
        }

    maximum = to_number(requirement.get("maximum_quantity"))
    if maximum is None:
        return {
            "criterion": "Quantity",
            "status": "NOT_APPLICABLE",
            "reason": "No valid quantity limit."
        }

    quantity = to_number(patient.get("quantity"))
    if quantity is None:
        return {
            "criterion": "Quantity",
            "status": "UNKNOWN",
            "reason": "Requested quantity is missing."
        }

    if quantity <= maximum:
        return {
            "criterion": "Quantity",
            "status": "PASSED",
            "reason": f"Requested quantity {quantity:g} is within the maximum allowed quantity of {maximum:g}."
        }

    return {
        "criterion": "Quantity",
        "status": "FAILED",
        "reason": f"Requested quantity {quantity:g} exceeds the maximum allowed quantity of {maximum:g}."
    }


# ============================================================
# FREQUENCY
# ============================================================

def check_frequency(
    patient: Dict[str, Any],
    policy: Dict[str, Any]
):
    requirement = policy.get("frequency_limit")
    if not requirement:
        return {
            "criterion": "Frequency",
            "status": "NOT_APPLICABLE",
            "reason": "No frequency limit."
        }

    frequency = patient.get("frequency")
    quantity = to_number(patient.get("quantity"))
    max_freq_qty = to_number(requirement.get("maximum_quantity"))

    if not frequency:
        if quantity is not None and max_freq_qty is not None and quantity <= max_freq_qty:
            return {
                "criterion": "Frequency",
                "status": "PASSED",
                "reason": f"Requested quantity ({quantity:g}) does not exceed policy frequency limit ({max_freq_qty:g} per {requirement.get('time_period_days', 180)} days)."
            }
        return {
            "criterion": "Frequency",
            "status": "UNKNOWN",
            "reason": "Frequency information is missing."
        }

    return {
        "criterion": "Frequency",
        "status": "PASSED",
        "reason": f"Frequency information ('{frequency}') is documented."
    }


# ============================================================
# POLICY EVALUATION
# ============================================================

def evaluate_policy(
    patient: Dict[str, Any],
    policy: Dict[str, Any]
) -> Dict[str, Any]:
    results = [
        check_cpt_hcpcs(patient, policy),
        check_diagnosis(patient, policy),
        check_age(patient, policy),
        check_severity(patient, policy),
        check_previous_treatment(patient, policy),
        check_previous_procedure(patient, policy),
        check_provider_specialty(patient, policy),
        check_facility(patient, policy),
        check_documentation(patient, policy),
        check_quantity(patient, policy),
        check_frequency(patient, policy),
    ]

    failed = [res for res in results if res["status"] == "FAILED"]
    unknown = [res for res in results if res["status"] == "UNKNOWN"]

    manual_review = []
    clinical_information = patient.get("clinical_information", {})
    if isinstance(clinical_information, dict) and clinical_information.get("contradictory_information") is True:
        manual_review.append("Required clinical information is contradictory")

    if failed:
        decision = "DENIED"
        reason = "Request denied due to explicit policy non-compliance: " + "; ".join([res["reason"] for res in failed])
    elif unknown or manual_review:
        decision = "MANUAL REVIEW"
        missing_reasons = [res["reason"] for res in unknown] + manual_review
        reason = "Required policy evidence was not available in the submitted documents: " + "; ".join(missing_reasons)
    else:
        decision = "APPROVED"
        reason = "All required policy criteria were satisfied."

    return {
        "decision": decision,
        "reason": reason,
        "policy_id": policy.get("policy_id"),
        "policy_name": policy.get("policy_name"),
        "results": results,
        "failed_criteria": [res["reason"] for res in failed],
        "manual_review_reasons": [res["reason"] for res in unknown] + manual_review,
        "missing_information": [res["criterion"] for res in unknown]
    }
"""
app.py - High-End Healthcare Prior Authorization Case Management Application

Orchestrates prior authorization intake, ML risk prediction, deterministic
policy evaluation, and Supabase PostgreSQL persistence with a clinical SaaS UI.
"""

from pathlib import Path
import logging
import os
from datetime import datetime
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv

# Ensure .env is reloaded on each run
load_dotenv(override=True)

import streamlit as st

from src.pdf_extractor import extract_text_from_pdf
from src.patient_parser import parse_patient, validate_patient
from src.normalizer import normalize_patient
from src.policy_matcher import load_policies
from src.decision import load_no_prior_auth, process_decision
from src.patient_verifier import (
    extract_identity_fields_locally,
    verify_patient_documents,
    deidentify_text,
    calculate_age_from_dob,
)
from src.database import (
    is_database_configured,
    check_database_status,
    save_patient,
    create_authorization_request,
    save_prediction,
    save_decision,
    save_decision_criteria,
    update_authorization_request_status,
    update_patient_clinical_data,
    update_authorization_request_details,
    get_recent_requests,
    get_decision_criteria,
)
from src.auth import init_auth_session, render_login_page
from src.predictor import predict_authorization
from src.ui import (
    apply_custom_styles,
    render_top_header,
    render_sidebar_nav,
    render_dashboard_view,
    render_all_requests_view,
    render_case_view,
    render_policies_view,
    render_audit_view,
    render_empty_state,
    render_error_state,
    render_intake_stage_tracker,
    render_verification_status,
    format_iso_timestamp,
    safe_str,
    safe_title,
    safe_upper,
)

logger = logging.getLogger(__name__)

# ============================================================
# PATHS & CONFIGURATION
# ============================================================

ROOT_DIR = Path(__file__).resolve().parent
POLICY_PATH = ROOT_DIR / "data" / "policies.json"
NO_PA_PATH = ROOT_DIR / "data" / "no_prior_auth.json"


# Page configuration
st.set_page_config(
    page_title="PREAUTH — Prior Authorization Management",
    page_icon="✚",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Apply unified clinical CSS design system
apply_custom_styles()


# ============================================================
# SESSION STATE INITIALIZATION
# ============================================================

if "active_case" not in st.session_state:
    st.session_state.active_case = None

if "nav_page" not in st.session_state:
    st.session_state.nav_page = "dashboard"


# ============================================================
# HELPER FUNCTIONS TO BUILD CASE OBJECTS
# ============================================================

def build_case_from_db_record(record: Dict[str, Any]) -> Dict[str, Any]:
    """
    Transforms a Supabase authorization request record into the unified
    'One Authorization = One Case' data structure.
    """
    req_id = record.get("id")
    p_data = record.get("patients") or {}
    decisions_list = record.get("decisions") or []
    predictions_list = record.get("predictions") or []

    # 1. Decision details
    if decisions_list and len(decisions_list) > 0:
        dec_obj = decisions_list[0]
        dec_id = dec_obj.get("id")
        final_decision = dec_obj.get("final_decision", record.get("request_status", "UNKNOWN"))
        policy_id = dec_obj.get("policy_id") or "POL-001"
        policy_name = dec_obj.get("policy_name") or "Medical Coverage Policy"
        failed_criteria = dec_obj.get("failed_criteria") or []
        manual_flags = dec_obj.get("manual_review_reasons") or []
        reason = dec_obj.get("reason", "")
    else:
        dec_id = None
        final_decision = record.get("request_status", "PENDING")
        policy_id = "POL-001"
        policy_name = "Medical Coverage Policy"
        failed_criteria = []
        manual_flags = []
        reason = ""

    # 2. Criteria retrieval
    criteria_list = []
    if dec_id:
        try:
            criteria_list = get_decision_criteria(dec_id)
        except Exception as e:
            logger.warning(f"Failed to fetch criteria for decision {dec_id}: {e}")

    # 3. Prediction details
    pred_data = predictions_list[0] if predictions_list and len(predictions_list) > 0 else {}

    # 4. PDF not stored locally
    matched_pdf_bytes = None
    matched_pdf_name = f"Patient_{p_data.get('patient_id', 'Record')}.pdf"
    matched_pdf_size = "PDF Document"

    return {
        "patient": p_data,
        "request": record,
        "decision": {
            "id": dec_id,
            "policy_id": policy_id,
            "policy_name": policy_name,
            "decision": final_decision,
            "reason": reason,
            "failed_criteria": failed_criteria,
            "manual_review_reasons": manual_flags,
        },
        "prediction": pred_data,
        "criteria": criteria_list,
        "pdf": {
            "filename": matched_pdf_name,
            "bytes": matched_pdf_bytes,
            "size_str": matched_pdf_size,
        },
        "audit": {
            "patient_db_id": p_data.get("id"),
            "request_id": req_id,
            "decision_id": dec_id,
            "created_at": record.get("created_at"),
        }
    }


def select_case_callback(record: Dict[str, Any]):
    """Callback triggered when user clicks 'Open Case' on any request card."""
    case_obj = build_case_from_db_record(record)
    st.session_state.active_case = case_obj
    st.rerun()


def back_to_requests_callback():
    """Callback triggered when user clicks 'Back to Requests' inside a case."""
    st.session_state.active_case = None


# ============================================================
# MAIN APPLICATION WORKFLOW
# ============================================================

def main():
    # 0. Initialize Auth Session & Guard App Access
    init_auth_session()
    if not st.session_state.get("authenticated", False):
        render_login_page()
        return

    # 1. Fetch DB Status & History Records
    db_status = check_database_status()
    try:
        all_requests = get_recent_requests(limit=100)
    except Exception as e:
        logger.error(f"Error loading requests from Supabase: {e}")
        all_requests = []

    # 2. Render Global App Header & Sidebar Nav
    render_top_header(db_status)
    nav_view = render_sidebar_nav(db_status)

    # If an active case is selected, render the unified Case View
    if st.session_state.active_case is not None:
        render_case_view(st.session_state.active_case, on_back_callback=back_to_requests_callback)
        return

    # 3. Render Selected View
    if nav_view == "dashboard":
        render_dashboard_view(
            requests=all_requests,
            on_select_case_callback=select_case_callback
        )

    elif nav_view == "requests":
        render_all_requests_view(
            requests=all_requests,
            on_select_case_callback=select_case_callback
        )

    elif nav_view == "upload":
        render_intake_pipeline(all_requests)

    elif nav_view == "policies":
        try:
            policies_data = load_policies(POLICY_PATH)
        except Exception:
            policies_data = []
        render_policies_view(policies_data)

    elif nav_view == "audit":
        render_audit_view(db_status, all_requests)


# ============================================================
# INTAKE PIPELINE COMPONENT (NEW REQUEST)
# ============================================================

def render_intake_pipeline(existing_requests: List[Dict[str, Any]]):
    """
    Renders the privacy-preserving dual document upload and end-to-end clinical evaluation pipeline.
    """
    st.markdown(
        """
        <div style="margin-bottom: 18px;">
            <h2 style="margin: 0 0 4px 0; font-size: 24px; font-weight: 700;">New Authorization Intake</h2>
            <p style="color: var(--slate-500); margin: 0; font-size: 14px;">Upload Patient History & Prior Auth Form PDFs for privacy-preserving identity verification and clinical rule evaluation.</p>
        </div>
        """,
        unsafe_allow_html=True
    )

    # Stage tracker UI
    render_intake_stage_tracker(current_stage=1)

    col_up, col_guide = st.columns([1.6, 0.9])

    with col_up:
        st.markdown("<h4 style='font-size: 15px; font-weight: 700; margin-bottom: 12px;'>Patient Documents Intake</h4>", unsafe_allow_html=True)
        col_doc1, col_doc2 = st.columns(2)

        with col_doc1:
            st.markdown(
                """
                <div style="border: 1px dashed var(--slate-300); border-radius: var(--radius-md); padding: 12px; background: white; margin-bottom: 8px;">
                    <div style="font-weight: 700; font-size: 13px; color: var(--slate-800);">📄 Patient History PDF</div>
                    <div style="font-size: 11px; color: var(--slate-500);">Medical history & chart PDF</div>
                </div>
                """,
                unsafe_allow_html=True
            )
            history_file = st.file_uploader(
                "Upload Patient History",
                type=["pdf"],
                key="history_pdf_uploader",
                label_visibility="collapsed"
            )

        with col_doc2:
            st.markdown(
                """
                <div style="border: 1px dashed var(--slate-300); border-radius: var(--radius-md); padding: 12px; background: white; margin-bottom: 8px;">
                    <div style="font-weight: 700; font-size: 13px; color: var(--slate-800);">📄 Prior Authorization Form PDF</div>
                    <div style="font-size: 11px; color: var(--slate-500);">PA request form PDF</div>
                </div>
                """,
                unsafe_allow_html=True
            )
            pa_file = st.file_uploader(
                "Upload Prior Auth Form",
                type=["pdf"],
                key="pa_pdf_uploader",
                label_visibility="collapsed"
            )

        # Single file or dual file detection
        if history_file is not None or pa_file is not None:
            doc_count = (1 if history_file else 0) + (1 if pa_file else 0)

            st.markdown(
                f"""
                <div style="background: #ffffff; border: 1px solid var(--slate-200); border-radius: 8px; padding: 12px 16px; margin: 12px 0;">
                    <div style="font-size: 13px; font-weight: 600; color: var(--slate-900);">📑 {doc_count} Document(s) Ready</div>
                    <div style="font-size: 11px; color: var(--slate-500);">Local PII extraction & identity verification active before AI parsing.</div>
                </div>
                """,
                unsafe_allow_html=True
            )

            if st.button("Verify Documents & Evaluate Prior Authorization →", type="primary", use_container_width=True, key="btn_run_eval"):
                run_clinical_evaluation_pipeline(history_file, pa_file)

    with col_guide:
        st.markdown(
            """
            <div style="background: #ffffff; border: 1px solid var(--slate-200); border-radius: var(--radius-lg); padding: 18px 20px;">
                <h4 style="font-size: 14px; font-weight: 700; margin: 0 0 8px 0;">Privacy & Intake Stages</h4>
                <div style="font-size: 12px; color: var(--slate-600); line-height: 1.6;">
                    1. <strong>Local PDF Extraction:</strong> Extract text locally (PyMuPDF).<br/>
                    2. <strong>Identity Matching:</strong> Cross-verify Member ID, DOB, Name locally.<br/>
                    3. <strong>Hard Gate:</strong> Stop immediately if documents mismatch.<br/>
                    4. <strong>PII Isolation:</strong> Strip PII; replace DOB with calculated age.<br/>
                    5. <strong>LLM Clinical Analysis:</strong> Pass non-PII clinical narrative.<br/>
                    6. <strong>Rule Engine Evaluation:</strong> Evaluate criteria against medical policy.<br/>
                    7. <strong>Determination:</strong> Produce final explainable case determination.
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )


def run_clinical_evaluation_pipeline(history_file, pa_file):
    """Executes the privacy-preserving dual document prior authorization evaluation pipeline."""
    try:
        # Validate inputs
        if history_file is None and pa_file is None:
            st.error("Please upload at least one clinical document PDF.")
            return

        # Use primary uploaded file as main reference if only one provided
        primary_file = pa_file if pa_file is not None else history_file
        history_ref = history_file if history_file is not None else pa_file
        pa_ref = pa_file if pa_file is not None else history_file

        pdf_bytes = primary_file.getvalue()
        pdf_size_kb = len(pdf_bytes) / 1024.0

        # Step 1: Extract text locally from both PDFs
        with st.spinner("Step 1/5 Extracting document text locally..."):
            history_text = extract_text_from_pdf(history_ref)
            pa_text = extract_text_from_pdf(pa_ref)

        if not history_text.strip() and not pa_text.strip():
            st.error("The uploaded PDF documents do not contain extractable text. Please ensure valid PDFs are uploaded.")
            return

        # Step 2: Extract identity fields locally & run deterministic verification
        with st.spinner("Step 2/5 Verifying patient identity deterministically (Local PII Engine)..."):
            hist_identity = extract_identity_fields_locally(history_text)
            pa_identity = extract_identity_fields_locally(pa_text)
            verification = verify_patient_documents(hist_identity, pa_identity)

        # Render Identity Verification Card
        render_verification_status(verification)

        # ── CRITICAL GATE: Hard stop on mismatch ──
        if not verification.get("verified", False):
            st.error("Identity verification failed. Downstream AI processing and policy evaluation have been stopped for patient privacy and security.")
            
            mismatch_case = {
                "patient": {
                    "patient_name": patient_name,
                    "patient_id": patient_id_val,
                    "age": calc_age,
                    "gender": gender_val,
                    "payer": "N/A"
                },
                "verification": verification,
                "request": {
                    "id": db_request_id or "REQ-VERIFICATION-FAILED",
                    "requested_service": "N/A",
                    "cpt_hcpcs_code": "N/A",
                    "payer": "N/A",
                    "status": "DOCUMENT VERIFICATION FAILED",
                    "created_at": datetime.utcnow().isoformat()
                },
                "decision": {
                    "id": None,
                    "policy_id": "N/A",
                    "policy_name": "Identity Verification Check",
                    "decision": "DOCUMENT VERIFICATION FAILED",
                    "reason": "Identity verification between submitted Patient History and PA Request Form failed.",
                    "failed_criteria": verification.get("discrepancies") or ["Document identity mismatch"],
                    "manual_review_reasons": []
                },
                "criteria": [],
                "prediction": {},
                "pdf": {
                    "filename": primary_file.name,
                    "bytes": pdf_bytes,
                    "size_str": f"{pdf_size_kb:.1f} KB"
                },
                "audit": {
                    "patient_db_id": db_patient_id,
                    "request_id": db_request_id,
                    "decision_id": None,
                    "created_at": datetime.utcnow().isoformat()
                }
            }

            if db_request_id:
                try:
                    update_authorization_request_status(db_request_id, "DOCUMENT VERIFICATION FAILED")
                except Exception as dec_err:
                    logger.warning(f"Failed to update verification failed status in DB: {dec_err}")

            st.session_state.active_case = mismatch_case
            st.rerun()
            return

        # ── PRE-PERSIST VERIFIED PII TO SUPABASE BEFORE GROQ ──
        norm_hist = verification.get("history_identity") or {}
        norm_pa = verification.get("pa_identity") or {}
        patient_name = norm_hist.get("name") or norm_pa.get("name") or "Verified Patient"
        patient_id_val = norm_hist.get("patient_id") or norm_hist.get("member_id") or norm_pa.get("member_id") or "PAT-001"
        calc_age = verification.get("calculated_age")
        gender_val = norm_hist.get("gender") or norm_pa.get("gender")

        initial_pii_patient = {
            "patient_id": patient_id_val,
            "patient_name": patient_name,
            "age": calc_age,
            "gender": gender_val,
            "payer": "Pending Evaluation",
        }

        db_patient_id = None
        db_request_id = None
        with st.spinner("Step 3/5 Storing verified PII data in Supabase & securing privacy boundary..."):
            try:
                db_patient_id = save_patient(initial_pii_patient)
                db_request_id = create_authorization_request(
                    db_patient_id,
                    initial_pii_patient,
                    status="PROCESSING"
                )
            except Exception as db_err:
                logger.warning(f"Database PII pre-persistence skipped: {db_err}")

        # Display UI feedback confirming PII is isolated & pre-saved in Supabase
        st.info("🔒 Verified PII data saved directly to Supabase. Processing de-identified clinical narrative with Groq AI...", icon="🔒")

        # Step 3: De-identification & PII Separation Layer
        calc_age = verification.get("calculated_age")
        deidentified_hist = deidentify_text(history_text, verification["history_identity"], calc_age)
        deidentified_pa = deidentify_text(pa_text, verification["pa_identity"], calc_age)

        # Combined deidentified clinical text (ZERO PII transmitted to LLM)
        deidentified_clinical_text = f"{deidentified_hist}\n\n{deidentified_pa}".strip()

        # Step 4: Pass de-identified text to Groq LLM for clinical parsing
        with st.spinner("Step 4/5 Parsing clinical facts with AI (De-Identified Narrative)..."):
            patient = parse_patient(deidentified_clinical_text)

            # Ensure calculated age is assigned if LLM did not extract age
            if patient.get("age") is None and calc_age is not None:
                patient["age"] = calc_age

            # Restore verified patient identity fields for local display & DB record update
            patient["patient_name"] = patient_name
            patient["patient_id"] = patient_id_val

        # ── CRITICAL: Stop immediately if CPT code is missing ──
        cpt_value = patient.get("cpt_hcpcs_code")
        if not cpt_value or str(cpt_value).strip().upper() in ("", "N/A", "NONE", "NULL"):
            st.error(
                "🚫 **CPT / HCPCS Code Not Found** — The uploaded clinical document "
                "does not contain a valid CPT or HCPCS procedure code. "
                "A CPT code is required to match against coverage policies and "
                "evaluate prior authorization.\n\n"
                "**Please ensure the clinical document includes a CPT/HCPCS code** "
                "(e.g., 73721 for MRI Knee, 45378 for Colonoscopy) and re-upload.",
                icon="🚫"
            )
            return

        # Step 5: Normalize clinical coding standards & evaluate rules
        with st.spinner("Step 5/5 Evaluating coverage rules & medical policy determination..."):
            patient = normalize_patient(patient)
            validation = validate_patient(patient)

            # Update Supabase patient record with full clinical details
            if db_patient_id:
                try:
                    update_patient_clinical_data(db_patient_id, patient)
                    update_authorization_request_details(db_request_id, patient, status="EVALUATING")
                except Exception as update_err:
                    logger.warning(f"Could not update patient clinical details in Supabase: {update_err}")

            # ML Prediction Signal
            prediction_res = predict_authorization(patient)
            if db_request_id and prediction_res.get("status") == "success":
                try:
                    save_prediction(db_request_id, prediction_res)
                except Exception as pred_err:
                    logger.warning(f"Failed to persist prediction: {pred_err}")

            # Policy Matching & Deterministic Rule Engine Evaluation
            policies = load_policies(POLICY_PATH)
            no_pa_codes = load_no_prior_auth(NO_PA_PATH)
            result = process_decision(patient, policies, no_pa_codes)

            # Persist Final Decision & Criteria to Supabase
            db_decision_id = None
            criteria_to_save = result.get("criteria") or result.get("results") or []
            if db_request_id and result:
                try:
                    db_decision_id = save_decision(db_request_id, result)
                    save_decision_criteria(db_decision_id, criteria_to_save)
                    update_authorization_request_status(
                        db_request_id,
                        result.get("decision", "MANUAL REVIEW")
                    )
                except Exception as dec_err:
                    logger.warning(f"Failed to persist final decision: {dec_err}")

        # Package into Unified Case Object and display immediately
        case_obj = {
            "patient": patient,
            "verification": verification,
            "request": {
                "id": db_request_id or "REQ-NEW",
                "requested_service": patient.get("requested_service"),
                "cpt_hcpcs_code": patient.get("cpt_hcpcs_code"),
                "quantity": patient.get("quantity", "1"),
                "frequency": patient.get("frequency", "Single"),
                "payer": patient.get("payer"),
                "status": result.get("decision", "PENDING"),
                "created_at": datetime.utcnow().isoformat(),
            },
            "decision": {
                "id": db_decision_id,
                "policy_id": result.get("policy_id") or (result.get("policy", {}).get("policy_id") if result.get("policy") else "POL-001"),
                "policy_name": result.get("policy_name") or (result.get("policy", {}).get("policy_name") if result.get("policy") else "Medical Coverage Policy"),
                "decision": result.get("decision", "MANUAL REVIEW"),
                "reason": result.get("reason", ""),
                "failed_criteria": result.get("failed_criteria", []),
                "manual_review_reasons": result.get("manual_review_reasons", []),
            },
            "prediction": prediction_res,
            "criteria": criteria_to_save,
            "pdf": {
                "filename": primary_file.name,
                "bytes": pdf_bytes,
                "size_str": f"{pdf_size_kb:.1f} KB",
            },
            "audit": {
                "patient_db_id": db_patient_id,
                "request_id": db_request_id,
                "decision_id": db_decision_id,
                "created_at": datetime.utcnow().isoformat(),
            }
        }

        st.session_state.active_case = case_obj
        st.success("Prior authorization evaluation complete. Opening complete clinical case...")
        st.rerun()

    except Exception as e:
        logger.error(f"Pipeline error: {e}")
        render_error_state("An unexpected error occurred during clinical evaluation.", str(e))

    except Exception as e:
        logger.error(f"Pipeline error: {e}")
        render_error_state("An unexpected error occurred during clinical evaluation.", str(e))


if __name__ == "__main__":
    main()
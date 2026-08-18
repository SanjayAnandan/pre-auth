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
from src.database import (
    is_database_configured,
    check_database_status,
    save_patient,
    create_authorization_request,
    save_prediction,
    save_decision,
    save_decision_criteria,
    update_authorization_request_status,
    get_recent_requests,
    get_decision_criteria,
)
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
UPLOAD_DIR = ROOT_DIR / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

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

    # 4. Matching PDF Document from local uploads cache
    matched_pdf_bytes = None
    matched_pdf_name = f"Patient_{p_data.get('patient_id', 'Record')}.pdf"
    matched_pdf_size = "PDF Document"

    for p_file in UPLOAD_DIR.glob("*.pdf"):
        try:
            with open(p_file, "rb") as pf:
                matched_pdf_bytes = pf.read()
                matched_pdf_name = p_file.name
                matched_pdf_size = f"{len(matched_pdf_bytes) / 1024.0:.1f} KB"
            break
        except Exception:
            pass

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
    Renders the document upload and end-to-end clinical evaluation pipeline.
    """
    st.markdown(
        """
        <div style="margin-bottom: 18px;">
            <h2 style="margin: 0 0 4px 0; font-size: 24px; font-weight: 700;">New Authorization Intake</h2>
            <p style="color: var(--slate-500); margin: 0; font-size: 14px;">Upload a clinical patient PDF document to evaluate coverage rules against medical policies.</p>
        </div>
        """,
        unsafe_allow_html=True
    )

    col_up, col_guide = st.columns([1.5, 1.0])

    with col_up:
        uploaded_file = st.file_uploader(
            "Upload clinical record PDF",
            type=["pdf"],
            help="Upload a structured patient clinical record or medical chart PDF.",
            key="intake_pdf_uploader"
        )

        if uploaded_file is not None:
            pdf_bytes = uploaded_file.getvalue()
            pdf_size_kb = len(pdf_bytes) / 1024.0

            st.markdown(
                f"""
                <div style="background: #ffffff; border: 1px solid var(--slate-200); border-radius: 8px; padding: 12px 16px; margin: 12px 0;">
                    <div style="font-size: 13px; font-weight: 600; color: var(--slate-900);">📄 {uploaded_file.name}</div>
                    <div style="font-size: 11px; color: var(--slate-500);">Size: {pdf_size_kb:.1f} KB • Ready for extraction & analysis</div>
                </div>
                """,
                unsafe_allow_html=True
            )

            if st.button("Evaluate Prior Authorization →", type="primary", use_container_width=True, key="btn_run_eval"):
                run_clinical_evaluation_pipeline(uploaded_file, pdf_bytes, pdf_size_kb)

    with col_guide:
        st.markdown(
            """
            <div style="background: #ffffff; border: 1px solid var(--slate-200); border-radius: var(--radius-lg); padding: 18px 20px;">
                <h4 style="font-size: 14px; font-weight: 700; margin: 0 0 8px 0;">Intake Evaluation Stages</h4>
                <div style="font-size: 12px; color: var(--slate-600); line-height: 1.6;">
                    1. <strong>Document Ingestion:</strong> Cache clinical PDF to uploads.<br/>
                    2. <strong>Text Extraction:</strong> Extract medical narrative via PDF engine.<br/>
                    3. <strong>Clinical Parsing:</strong> Extract diagnosis, ICD-10, CPT, severity.<br/>
                    4. <strong>Normalization:</strong> Standardize patient codes and clinical terms.<br/>
                    5. <strong>Supabase Registry:</strong> Save patient & authorization record.<br/>
                    6. <strong>AI Risk Signal:</strong> Score ML model approval probabilities.<br/>
                    7. <strong>Rule Engine:</strong> Deterministically test coverage criteria.<br/>
                    8. <strong>Determination:</strong> Produce final explainable case determination.
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )


def run_clinical_evaluation_pipeline(uploaded_file, pdf_bytes: bytes, pdf_size_kb: float):
    """Executes the full prior authorization evaluation pipeline."""
    try:
        # Step 1: Save PDF locally
        saved_pdf_path = UPLOAD_DIR / uploaded_file.name
        with open(saved_pdf_path, "wb") as f:
            f.write(pdf_bytes)

        # Step 2: Extract text
        with st.spinner("1/7 Ingesting document & extracting clinical text..."):
            raw_text = extract_text_from_pdf(uploaded_file)

        if not raw_text or not raw_text.strip():
            st.error("The uploaded PDF does not contain extractable text. Please ensure it is a valid clinical document.")
            return

        # Step 3: Parse patient information
        with st.spinner("2/7 Parsing clinical entities, procedures, and diagnosis..."):
            patient = parse_patient(raw_text)

        # Step 4: Normalize and validate
        with st.spinner("3/7 Normalizing clinical coding standards and medical terms..."):
            patient = normalize_patient(patient)
            validation = validate_patient(patient)

        # Step 5: Save patient & create authorization request in Supabase
        db_patient_id = None
        db_request_id = None
        with st.spinner("4/7 Persisting patient record in Supabase PostgreSQL..."):
            try:
                db_patient_id = save_patient(patient)
                db_request_id = create_authorization_request(
                    db_patient_id,
                    patient,
                    status="PENDING"
                )
            except Exception as db_err:
                logger.warning(f"Database insertion skipped: {db_err}")

        # Step 6: ML Prediction Signal
        with st.spinner("5/7 Generating AI risk signal and probability distribution..."):
            prediction_res = predict_authorization(patient)
            if db_request_id and prediction_res.get("status") == "success":
                try:
                    save_prediction(db_request_id, prediction_res)
                except Exception as pred_err:
                    logger.warning(f"Failed to persist prediction: {pred_err}")

        # Step 7: Policy Matching & Rule Engine Evaluation
        with st.spinner("6/7 Evaluating coverage guidelines against medical policy rules..."):
            policies = load_policies(POLICY_PATH)
            no_pa_codes = load_no_prior_auth(NO_PA_PATH)
            result = process_decision(patient, policies, no_pa_codes)

        # Step 8: Save Final Decision & Criteria
        db_decision_id = None
        criteria_to_save = result.get("criteria") or result.get("results") or []
        with st.spinner("7/7 Recording final determination and audit ledger..."):
            if db_request_id and result:
                try:
                    db_decision_id = save_decision(db_request_id, result)
                    save_decision_criteria(db_decision_id, criteria_to_save)
                    update_authorization_request_status(
                        db_request_id,
                        result.get("decision", "MANUAL REVIEW")
                    )
                except Exception as dec_err:
                    logger.warning(f"Failed to persist decision: {dec_err}")

        # Package into Unified Case Object and display immediately
        case_obj = {
            "patient": patient,
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
                "filename": uploaded_file.name,
                "bytes": pdf_bytes,
                "size_str": f"{pdf_size_kb:.1f} KB",
                "path": str(saved_pdf_path),
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


if __name__ == "__main__":
    main()
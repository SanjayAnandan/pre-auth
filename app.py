"""
app.py - High-End Healthcare Prior Authorization Case Management Application

Orchestrates prior authorization intake, deterministic policy evaluation,
and Supabase PostgreSQL persistence with a clinical SaaS UI.
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
from src.patient_parser import parse_patient, validate_patient, merge_patient_data
from src.normalizer import normalize_patient
from src.policy_matcher import load_policies, find_matching_policies
from src.decision import load_no_prior_auth, process_decision, select_policy_deterministically
from src.patient_insurance import validate_patient_coverage
from src.auth import init_auth_session, render_login_page, logout
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
    create_authorization_request_record,
    save_decision,
    save_decision_criteria,
    update_authorization_request_status,
    update_patient_clinical_data,
    update_authorization_request_details,
    get_recent_requests,
    get_decision_criteria,
    save_document_metadata,
    save_identity_verification,
    save_clinical_facts,
    get_patient_insurance,
)
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
    render_processing_policy_validation,
    render_processing_insurance_validation,
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
    if not isinstance(record, dict):
        record = {}

    req_id = record.get("id")
    p_data = record.get("patients") or {}
    decisions_list = record.get("decisions") or []

    # 1. Decision details — pick the latest decision (most recent created_at)
    valid_decisions = [d for d in decisions_list if isinstance(d, dict)]
    if valid_decisions:
        sorted_decisions = sorted(
            valid_decisions,
            key=lambda d: str(d.get("created_at") or ""),
            reverse=True
        )
        dec_obj = sorted_decisions[0]
        dec_id = dec_obj.get("id")
        final_decision = str(dec_obj.get("final_decision") or record.get("request_status") or "PENDING").upper()
        policy_id = dec_obj.get("policy_id") or "POL-001"
        policy_name = dec_obj.get("policy_name") or "Medical Coverage Policy"
        failed_criteria = dec_obj.get("failed_criteria") or []
        manual_flags = dec_obj.get("manual_review_reasons") or []
        reason = dec_obj.get("reason", "")
    else:
        dec_id = None
        final_decision = str(record.get("request_status") or "PENDING").upper()
        policy_id = "POL-001"
        policy_name = "Medical Coverage Policy"
        failed_criteria = []
        manual_flags = []
        reason = ""

    # 2. Criteria retrieval
    criteria_list = []
    if dec_id:
        try:
            criteria_list = get_decision_criteria(dec_id) or []
        except Exception as e:
            logger.warning(f"Failed to fetch criteria for decision {dec_id}: {e}")

    # 3. PDF not stored locally
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


def handle_resubmission_callback(case_data: Dict[str, Any], uploaded_pdfs):
    """
    Handles the Manual Review -> Supplemental Upload (single or multiple PDFs) -> Merge -> Deterministic Re-evaluation workflow.
    """
    try:
        if not uploaded_pdfs:
            st.error("Please select at least one PDF document to upload.")
            return

        pdf_list = uploaded_pdfs if isinstance(uploaded_pdfs, list) else [uploaded_pdfs]
        if len(pdf_list) == 0:
            st.error("Please select at least one PDF document to upload.")
            return

        db_request_id = case_data.get("audit", {}).get("request_id") or case_data.get("request", {}).get("id")
        db_patient_id = case_data.get("audit", {}).get("patient_db_id") or case_data.get("patient", {}).get("id")

        existing_patient = case_data.get("patient") or {}
        merged_patient = dict(existing_patient)

        with st.spinner("Processing additional clinical information..."):
            for pdf_file in pdf_list:
                supp_text = extract_text_from_pdf(pdf_file)
                if not supp_text or not supp_text.strip():
                    st.error(f"Unable to extract text from document '{getattr(pdf_file, 'name', 'Uploaded File')}'. Please upload a text-based clinical report PDF.")
                    return

                supp_patient = parse_patient(supp_text)
                merged_patient = merge_patient_data(merged_patient, supp_patient)

                if db_request_id and hasattr(pdf_file, 'name'):
                    try:
                        supp_bytes = pdf_file.getvalue() if hasattr(pdf_file, 'getvalue') else None
                        save_document_metadata(db_request_id, "Supplemental Evidence", pdf_file.name, "VERIFIED", pdf_bytes=supp_bytes)
                    except Exception as doc_err:
                        logger.warning(f"Could not persist supplemental document metadata: {doc_err}")

        with st.spinner("Re-evaluating policy criteria..."):
            merged_patient = normalize_patient(merged_patient)

            policies = load_policies(POLICY_PATH)
            no_pa_codes = load_no_prior_auth(NO_PA_PATH)

            selected_policy_id = case_data.get("decision", {}).get("policy_id")
            target_policy = next((p for p in policies if p.get("policy_id") == selected_policy_id), None)

            if target_policy:
                from src.rule_engine import evaluate_policy
                eval_result = evaluate_policy(merged_patient, target_policy)
            else:
                eval_result = process_decision(merged_patient, policies, no_pa_codes)

            new_decision_id = None
            criteria_to_save = eval_result.get("results") or eval_result.get("criteria") or []
            new_status = eval_result.get("decision", "MANUAL REVIEW")

            if db_patient_id:
                try:
                    update_patient_clinical_data(db_patient_id, merged_patient)
                except Exception as e:
                    logger.warning(f"Could not update patient in database: {e}")

            if db_request_id and isinstance(db_request_id, str):
                try:
                    update_authorization_request_details(db_request_id, merged_patient, status="EVALUATING")
                    save_clinical_facts(db_request_id, merged_patient, model_name="Groq LLM")
                    new_decision_id = save_decision(db_request_id, eval_result)
                    if new_decision_id:
                        save_decision_criteria(new_decision_id, criteria_to_save)
                    update_authorization_request_status(db_request_id, new_status)
                except Exception as e:
                    logger.warning(f"Could not persist re-evaluated decision: {e}")

            updated_case = dict(case_data)
            updated_case["resubmitted"] = True
            updated_case["patient"] = merged_patient
            updated_case["request"] = dict(case_data.get("request", {}))
            updated_case["request"]["status"] = new_status
            updated_case["decision"] = {
                "id": new_decision_id or case_data.get("decision", {}).get("id"),
                "policy_id": eval_result.get("policy_id") or case_data.get("decision", {}).get("policy_id"),
                "policy_name": eval_result.get("policy_name") or case_data.get("decision", {}).get("policy_name"),
                "decision": new_status,
                "reason": eval_result.get("reason", ""),
                "failed_criteria": eval_result.get("failed_criteria", []),
                "manual_review_reasons": eval_result.get("manual_review_reasons", []),
            }
            updated_case["criteria"] = criteria_to_save

            st.session_state.active_case = updated_case
            st.success(f"Policy re-evaluated successfully. Updated Decision: {new_status}")
            st.rerun()

    except Exception as e:
        logger.error(f"Error during supplemental document re-evaluation: {e}")
        render_error_state("Failed to process supplemental clinical document.", str(e))


# ============================================================
# MAIN APPLICATION WORKFLOW
# ============================================================

def main():
    # 0. Initialize Auth Session & Application Gating
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
        render_case_view(
            st.session_state.active_case,
            on_back_callback=back_to_requests_callback,
            on_resubmit_callback=handle_resubmission_callback
        )
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

        uploaded_files = [f for f in (history_file, pa_file) if f is not None]

        # Use primary uploaded file as main reference if only one provided
        primary_file = uploaded_files[0]
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

        # Compute deterministic SHA-256 document hash from uploaded document text
        from src.patient_parser import compute_document_hash
        doc_hash = compute_document_hash(f"{history_text}\n\n{pa_text}")

        # Step 2: Extract identity fields locally & run deterministic verification
        with st.spinner("Step 2/5 Verifying patient identity deterministically (Local PII Engine)..."):
            hist_identity = extract_identity_fields_locally(history_text)
            pa_identity = extract_identity_fields_locally(pa_text)
            verification = verify_patient_documents(hist_identity, pa_identity)

        # Render Identity Verification Card
        render_verification_status(verification)

        # ── CRITICAL GATE: Hard stop on mismatch ──
        if not verification.get("verified", False):
            st.error("Identity verification failed. Further clinical processing and policy evaluation have been stopped for patient privacy and security.")
            return

        # ── PRE-PERSIST VERIFIED PII TO SUPABASE BEFORE GROQ ──
        norm_hist = verification.get("history_identity") or {}
        norm_pa = verification.get("pa_identity") or {}
        patient_name = norm_hist.get("name") or norm_pa.get("name") or "Verified Patient"
        patient_id_val = norm_hist.get("patient_id") or norm_hist.get("member_id") or norm_pa.get("member_id") or "PAT-001"
        calc_age = verification.get("calculated_age") or norm_hist.get("stated_age") or norm_pa.get("stated_age")
        gender_val = norm_hist.get("gender") or norm_pa.get("gender")

        initial_pii_patient = {
            "patient_id": patient_id_val,
            "patient_name": patient_name,
            "age": calc_age,
            "gender": gender_val,
            "payer": "Pending Evaluation",
            "_document_hash": doc_hash,
        }

        db_patient_id = None
        db_request_id = None
        db_request_created_at = None
        with st.spinner("Step 3/5 Storing verified PII data in Supabase & securing privacy boundary..."):
            try:
                db_patient_id = save_patient(initial_pii_patient)
                req_rec = create_authorization_request_record(
                    db_patient_id,
                    initial_pii_patient,
                    status="PROCESSING"
                )
                db_request_id = req_rec.get("id")
                db_request_created_at = req_rec.get("created_at")

                if db_request_id:
                    hist_status = "VERIFIED" if verification.get("verified") else "MISMATCH"
                    pa_status = "VERIFIED" if verification.get("verified") else "MISMATCH"
                    save_document_metadata(db_request_id, "Patient History", primary_file.name, hist_status, pdf_bytes=pdf_bytes)
                    if len(uploaded_files) > 1:
                        save_document_metadata(db_request_id, "PA Request Form", uploaded_files[1].name, pa_status)
                    save_identity_verification(db_request_id, verification)
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

            # Restore verified patient identity fields and document hash
            patient["patient_name"] = patient_name
            patient["patient_id"] = patient_id_val
            patient["_document_hash"] = doc_hash

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

        # Step 5: Patient Insurance Validation, Policy Retrieval & Deterministic Evaluation
        patient = normalize_patient(patient)
        validation = validate_patient(patient)

        # Update Supabase patient record with full clinical details
        if db_patient_id:
            try:
                update_patient_clinical_data(db_patient_id, patient)
                update_authorization_request_details(db_request_id, patient, status="EVALUATING")
                save_clinical_facts(db_request_id, patient, model_name="Groq LLM")
            except Exception as update_err:
                logger.warning(f"Could not update patient clinical details in Supabase: {update_err}")

        # ── POLICY RETRIEVAL & DETERMINISTIC EVALUATION ──
        policies = load_policies(POLICY_PATH)
        no_pa_codes = load_no_prior_auth(NO_PA_PATH)

        matching_pols = find_matching_policies(patient, policies)
        cand_pol = select_policy_deterministically(patient, matching_pols) if matching_pols else None

        if cand_pol:
            render_processing_policy_validation(cand_pol)

        raw_pol_stat = cand_pol.get("policy_status") if isinstance(cand_pol, dict) else None
        is_active_pol = (raw_pol_stat is not None) and (str(raw_pol_stat).strip().lower() == "active")

        if is_active_pol:
            with st.spinner("Evaluating coverage rules & medical policy determination..."):
                result = process_decision(patient, policies, no_pa_codes)
        else:
            st.info("Policy validation completed: INACTIVE. Rule evaluation not performed — Manual Review required.", icon="ℹ️")
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
        req_created_at = db_request_created_at or datetime.utcnow().isoformat()
        case_obj = {
            "patient": patient,
            "verification": verification,
            "insurance": result.get("insurance") or patient.get("insurance"),
            "coverage_validation": None,
            "policy": result.get("policy"),
            "request": {
                "id": db_request_id,
                "requested_service": patient.get("requested_service"),
                "cpt_hcpcs_code": patient.get("cpt_hcpcs_code"),
                "quantity": patient.get("quantity", "1"),
                "frequency": patient.get("frequency", "Single"),
                "payer": patient.get("payer"),
                "status": result.get("decision", "PENDING"),
                "created_at": req_created_at,
            },
            "decision": {
                "id": db_decision_id,
                "policy_id": result.get("policy_id") or (result.get("policy", {}).get("policy_id") if result.get("policy") else "POL-001"),
                "policy_name": result.get("policy_name") or (result.get("policy", {}).get("policy_name") if result.get("policy") else "Medical Coverage Policy"),
                "policy": result.get("policy"),
                "decision": result.get("decision", "MANUAL REVIEW"),
                "reason": result.get("reason", ""),
                "failed_criteria": result.get("failed_criteria", []),
                "manual_review_reasons": result.get("manual_review_reasons", []),
            },
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
                "created_at": req_created_at,
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
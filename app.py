from pathlib import Path

import streamlit as st

from src.pdf_extractor import extract_text_from_pdf
from src.patient_parser import (
    parse_patient,
    validate_patient
)
from src.normalizer import (
    basic_normalize_patient
)
from src.policy_matcher import load_policies
from src.decision import (
    load_no_prior_auth,
    process_decision
)


# ============================================================
# PATHS
# ============================================================

ROOT_DIR = Path(__file__).resolve().parent

POLICY_PATH = ROOT_DIR / "data" / "policies.json"
NO_PA_PATH = ROOT_DIR / "data" / "no_prior_auth.json"


# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="PriorAuth AI",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="collapsed",
)


# ============================================================
# CSS
# ============================================================

st.markdown(
    """
    <style>

    @import url(
        'https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,500;9..144,600;9..144,700&family=IBM+Plex+Mono:wght@400;500;600&family=IBM+Plex+Sans:wght@400;500;600;700&display=swap'
    );

    :root {
        --paper: #EEF1EF;
        --ink: #1B2430;
        --brand: #146356;
        --approve: #2F8F5B;
        --deny: #B94A3B;
        --review: #C98A2B;
        --highlight: #F5C84C;
        --surface: #F7F9F7;
        --muted: #68736F;
        --line: #DCE3DF;
    }

    /* ========================================================
       GLOBAL
       ======================================================== */

    .stApp {
        background: var(--paper);
        color: var(--ink);
    }

    .block-container {
        max-width: 1120px;
        padding-top: 2rem;
        padding-bottom: 3rem;
    }

    header {
        visibility: hidden;
    }

    #MainMenu {
        visibility: hidden;
    }

    footer {
        visibility: hidden;
    }

    /* ========================================================
       TYPOGRAPHY
       ======================================================== */

    h1,
    h2,
    h3 {
        font-family: "Fraunces", serif !important;
        color: var(--ink) !important;
    }

    h1 {
        font-size: 2.7rem !important;
        letter-spacing: -1.2px !important;
    }

    h2 {
        font-size: 1.8rem !important;
    }

    h3 {
        font-size: 1.3rem !important;
    }

    p,
    label,
    button {
        font-family: "IBM Plex Sans", sans-serif !important;
    }

    [data-testid="stCaptionContainer"] {
        color: var(--muted);
    }

    /* ========================================================
       CONTAINERS
       ======================================================== */

    [data-testid="stVerticalBlockBorderWrapper"] {
        background: var(--surface);
        border: none !important;
        border-radius: 18px !important;
        box-shadow:
            0 12px 35px rgba(27, 36, 48, 0.07);
    }

    /* ========================================================
       FILE UPLOADER
       ======================================================== */

    [data-testid="stFileUploader"] {
        background: var(--surface);
        border-radius: 16px;
    }

    /* ========================================================
       BUTTONS
       ======================================================== */

    .stButton > button {
        border-radius: 10px !important;
        font-weight: 600 !important;
    }

    /* ========================================================
       DECISION STAMPS
       ======================================================== */

    .decision-stamp-container {
        display: flex;
        align-items: center;
        justify-content: center;
        min-height: 170px;
    }

    .decision-stamp-approved {
        display: inline-block;

        color: var(--approve);
        border: 3px solid var(--approve);
        border-radius: 14px;

        padding: 17px 27px;

        font-family: "Fraunces", serif;
        font-size: 2.1rem;
        font-weight: 700;

        letter-spacing: 1.5px;

        transform: rotate(-2deg);

        animation:
            stampIn 420ms
            cubic-bezier(.175,.885,.32,1.275)
            both;

        box-shadow:
            0 8px 22px rgba(47, 143, 91, 0.10);
    }

    .decision-stamp-denied {
        display: inline-block;

        color: var(--deny);
        border: 3px solid var(--deny);
        border-radius: 14px;

        padding: 17px 27px;

        font-family: "Fraunces", serif;
        font-size: 2.1rem;
        font-weight: 700;

        letter-spacing: 1.5px;

        transform: rotate(-2deg);

        animation:
            stampIn 420ms
            cubic-bezier(.175,.885,.32,1.275)
            both;

        box-shadow:
            0 8px 22px rgba(185, 74, 59, 0.10);
    }

    .decision-stamp-review {
        display: inline-block;

        color: var(--review);
        border: 3px solid var(--review);
        border-radius: 14px;

        padding: 17px 27px;

        font-family: "Fraunces", serif;
        font-size: 2.1rem;
        font-weight: 700;

        letter-spacing: 1.5px;

        transform: rotate(-2deg);

        animation:
            stampIn 420ms
            cubic-bezier(.175,.885,.32,1.275)
            both;

        box-shadow:
            0 8px 22px rgba(201, 138, 43, 0.10);
    }

    @keyframes stampIn {

        from {
            opacity: 0;
            transform:
                rotate(-2deg)
                scale(0.75);
        }

        to {
            opacity: 1;
            transform:
                rotate(-2deg)
                scale(1);
        }
    }

    /* ========================================================
       REDUCED MOTION
       ======================================================== */

    @media (prefers-reduced-motion: reduce) {

        *,
        *::before,
        *::after {

            animation-duration: 0.01ms !important;

            animation-iteration-count: 1 !important;

            transition-duration: 0.01ms !important;
        }

    }

    /* ========================================================
       MOBILE
       ======================================================== */

    @media (max-width: 700px) {

        .block-container {
            padding-left: 1rem;
            padding-right: 1rem;
        }

        h1 {
            font-size: 2.2rem !important;
        }

        .decision-stamp-approved,
        .decision-stamp-denied,
        .decision-stamp-review {
            font-size: 1.6rem;
        }

    }

    </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# SESSION STATE
# ============================================================

if "page" not in st.session_state:
    st.session_state.page = "upload"

if "patient" not in st.session_state:
    st.session_state.patient = None

if "result" not in st.session_state:
    st.session_state.result = None

if "missing_fields" not in st.session_state:
    st.session_state.missing_fields = []


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def safe_title(value, default="Not provided"):
    """
    Safely convert a value to title case.
    """

    if value is None:
        return default

    value = str(value).strip()

    if not value:
        return default

    return value.title()


def safe_upper(value, default="Not provided"):
    """
    Safely convert a value to uppercase.
    """

    if value is None:
        return default

    value = str(value).strip()

    if not value:
        return default

    return value.upper()


def safe_display(value, default="Not provided"):
    """
    Safely display any patient field.
    """

    if value is None:
        return default

    if isinstance(value, str) and not value.strip():
        return default

    return str(value)


# ============================================================
# UPLOAD PAGE
# ============================================================

if st.session_state.page == "upload":

    # --------------------------------------------------------
    # Brand
    # --------------------------------------------------------

    st.title("🏥 PriorAuth AI")

    st.caption(
        "Intelligent Prior Authorization Decision Support"
    )

    st.divider()

    # --------------------------------------------------------
    # Hero
    # --------------------------------------------------------

    st.title("Prior Authorization Review")

    st.write(
        "Upload a patient record and let the policy engine "
        "evaluate the request against the applicable "
        "coverage requirements."
    )

    st.write("")

    # --------------------------------------------------------
    # Upload
    # --------------------------------------------------------

    with st.container(border=True):

        st.subheader("Patient Record")

        uploaded_file = st.file_uploader(
            "Upload patient PDF",
            type=["pdf"],
            help=(
                "Upload a structured patient record. "
                "The PDF is processed in memory and "
                "is not saved to the data folder."
            ),
        )

        if uploaded_file is not None:

            st.success(
                f"✓ {uploaded_file.name}"
            )

            st.caption(
                "Ready for authorization evaluation."
            )

            st.write("")

            evaluate = st.button(
                "Evaluate Prior Authorization →",
                type="primary",
                use_container_width=True,
            )

            if evaluate:

                try:

                    # ==================================================
                    # 1. PDF EXTRACTION
                    # ==================================================

                    with st.spinner(
                        "Reading patient record..."
                    ):

                        raw_text = extract_text_from_pdf(
                            uploaded_file
                        )

                    if not raw_text:

                        st.error(
                            "No text could be extracted "
                            "from this PDF."
                        )

                        st.stop()

                    if not raw_text.strip():

                        st.error(
                            "The PDF does not contain "
                            "extractable text."
                        )

                        st.stop()


                    # ==================================================
                    # 2. PATIENT EXTRACTION
                    # ==================================================
                    #
                    # The LLM extracts facts from the
                    # patient document.
                    #
                    # It does NOT yet know the policy.
                    #
                    # ==================================================

                    with st.spinner(
                        "Extracting patient details..."
                    ):

                        patient = parse_patient(
                            raw_text
                        )


                    # ==================================================
                    # 3. BASIC NORMALIZATION
                    # ==================================================
                    #
                    # Only safe formatting here.
                    #
                    # Examples:
                    #   " M25.561 " -> "M25.561"
                    #   "73721"      -> "73721"
                    #
                    # We DO NOT perform policy-aware
                    # semantic normalization here.
                    #
                    # ==================================================

                    patient = basic_normalize_patient(
                        patient
                    )


                    # ==================================================
                    # 4. LOAD POLICIES
                    # ==================================================

                    with st.spinner(
                        "Loading coverage policies..."
                    ):

                        policies = load_policies(
                            POLICY_PATH
                        )

                        no_pa_codes = load_no_prior_auth(
                            NO_PA_PATH
                        )


                    # ==================================================
                    # 5. BASIC VALIDATION
                    # ==================================================
                    #
                    # This validation checks whether we have
                    # enough information to identify/evaluate
                    # the authorization request.
                    #
                    # It does NOT check policy-specific
                    # requirements such as:
                    #
                    #   severity
                    #   provider specialty
                    #   documentation
                    #   previous treatment
                    #
                    # Those are checked AFTER the policy
                    # is identified.
                    #
                    # ==================================================

                    validation = validate_patient(
                        patient
                    )

                    missing_fields = validation.get(
                        "missing_fields",
                        []
                    )

                    st.session_state.missing_fields = (
                        missing_fields
                    )

                    if not validation.get(
                        "valid",
                        False
                    ):

                        readable_fields = [
                            field.replace(
                                "_",
                                " "
                            ).title()
                            for field in missing_fields
                        ]

                        st.error(
                            "The patient record is missing "
                            "information required to evaluate "
                            "the authorization request."
                        )

                        st.warning(
                            "Missing fields: "
                            + ", ".join(
                                readable_fields
                            )
                        )

                        st.stop()


                    # ==================================================
                    # 6. POLICY EVALUATION
                    # ==================================================
                    #
                    # IMPORTANT:
                    #
                    # process_decision() now performs:
                    #
                    #   1. No-PA check
                    #   2. Policy matching
                    #   3. Policy-aware normalization
                    #   4. Deterministic rule evaluation
                    #
                    # ==================================================

                    with st.spinner(
                        "Evaluating authorization criteria..."
                    ):

                        result = process_decision(
                            patient,
                            policies,
                            no_pa_codes
                        )


                    # ==================================================
                    # 7. STORE NORMALIZED PATIENT
                    # ==================================================
                    #
                    # process_decision() returns the patient AFTER
                    # policy-aware normalization.
                    #
                    # This is the version the decision page should
                    # display.
                    #
                    # ==================================================

                    normalized_patient = result.get(
                        "normalized_patient",
                        patient
                    )

                    st.session_state.patient = (
                        normalized_patient
                    )

                    st.session_state.result = (
                        result
                    )

                    st.session_state.page = "decision"

                    st.rerun()


                except Exception as e:

                    st.error(
                        "Something went wrong while "
                        "processing the patient record."
                    )

                    st.exception(e)


# ============================================================
# DECISION PAGE
# ============================================================

elif st.session_state.page == "decision":

    patient = st.session_state.patient

    result = st.session_state.result


    # ========================================================
    # SAFETY CHECK
    # ========================================================

    if patient is None or result is None:

        st.session_state.page = "upload"

        st.rerun()


    # ========================================================
    # NEW REQUEST
    # ========================================================

    if st.button("← New Request"):

        st.session_state.page = "upload"

        st.session_state.patient = None

        st.session_state.result = None

        st.session_state.missing_fields = []

        st.rerun()


    # ========================================================
    # HEADER
    # ========================================================

    st.title("🏥 PriorAuth AI")

    st.caption("Authorization Decision")

    st.divider()


    # ========================================================
    # REQUEST SUMMARY
    # ========================================================

    st.subheader("Request Summary")


    patient_id = patient.get(
        "patient_id"
    )

    payer = patient.get(
        "payer"
    )

    service = patient.get(
        "requested_service"
    )

    code = patient.get(
        "cpt_hcpcs_code"
    )


    # ========================================================
    # SAFE DISPLAY VALUES
    # ========================================================

    patient_id_display = safe_display(
        patient_id
    )

    payer_display = safe_title(
        payer
    )

    service_display = safe_title(
        service
    )

    code_display = safe_upper(
        code
    )


    # ========================================================
    # SUMMARY CARDS
    # ========================================================

    col1, col2, col3, col4 = st.columns(
        [1, 1, 2.3, 1]
    )


    with col1:

        st.metric(
            "PATIENT ID",
            patient_id_display
        )


    with col2:

        st.metric(
            "PAYER",
            payer_display
        )


    with col3:

        st.metric(
            "REQUESTED SERVICE",
            service_display
        )


    with col4:

        st.metric(
            "CPT / HCPCS",
            code_display
        )


    st.write("")


    # ========================================================
    # MISSING INFORMATION WARNING
    # ========================================================

    missing_fields = st.session_state.get(
        "missing_fields",
        []
    )


    if missing_fields:

        with st.container(border=True):

            st.warning(
                "Some patient information could not "
                "be extracted from the submitted PDF."
            )

            readable_fields = [
                field.replace(
                    "_",
                    " "
                ).title()
                for field in missing_fields
            ]

            st.caption(
                "Missing fields: "
                + ", ".join(readable_fields)
            )


    # ========================================================
    # DECISION
    # ========================================================

    decision = result.get(
        "decision",
        "MANUAL_REVIEW"
    )


    # ========================================================
    # TWO COLUMN DECISION AREA
    # ========================================================

    decision_col, reason_col = st.columns(
        [0.85, 1.65],
        gap="large"
    )


    # ========================================================
    # LEFT: FINAL DECISION
    # ========================================================

    with decision_col:

        with st.container(border=True):

            st.subheader("Final Decision")


            if decision == "APPROVED":

                st.markdown(
                    """
                    <div class="decision-stamp-container">
                        <div class="decision-stamp-approved">
                            APPROVED
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

                st.success(
                    "The request satisfies the "
                    "applicable policy requirements."
                )


            elif decision == "DENIED":

                st.markdown(
                    """
                    <div class="decision-stamp-container">
                        <div class="decision-stamp-denied">
                            DENIED
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

                st.error(
                    "The request does not satisfy one "
                    "or more policy requirements."
                )


            elif decision == "MANUAL_REVIEW":

                st.markdown(
                    """
                    <div class="decision-stamp-container">
                        <div class="decision-stamp-review">
                            MANUAL REVIEW
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

                st.warning(
                    "The request requires additional review."
                )


            elif decision == "NO_PRIOR_AUTH_REQUIRED":

                st.success(
                    "NO PRIOR AUTHORIZATION REQUIRED"
                )


            else:

                st.warning(
                    safe_display(
                        decision,
                        "UNKNOWN"
                    )
                )


    # ========================================================
    # RIGHT: REASONING
    # ========================================================

    with reason_col:

        with st.container(border=True):

            st.subheader(
                "Decision Explanation"
            )


            if decision == "DENIED":

                failed_count = sum(
                    1
                    for criterion in result.get(
                        "criteria",
                        []
                    )
                    if criterion.get(
                        "status"
                    ) == "FAILED"
                )

                st.write(
                    f"The request failed "
                    f"**{failed_count}** "
                    "policy requirement(s)."
                )


            elif decision == "APPROVED":

                passed_count = sum(
                    1
                    for criterion in result.get(
                        "criteria",
                        []
                    )
                    if criterion.get(
                        "status"
                    ) == "PASSED"
                )

                st.write(
                    f"The request satisfied "
                    f"**{passed_count}** "
                    "policy requirement(s)."
                )


            elif decision == "MANUAL_REVIEW":

                st.write(
                    result.get(
                        "reason",
                        "No applicable policy was found "
                        "for the requested service."
                    )
                )


            else:

                st.write(
                    result.get(
                        "reason",
                        "Policy evaluation completed."
                    )
                )


            # ==================================================
            # POLICY EVALUATION NOTICE
            # ==================================================

            st.info(
                "Policy criteria were evaluated against "
                "the submitted patient information."
            )


            # ==================================================
            # POLICY CRITERIA
            # ==================================================

            st.subheader(
                "Policy Criteria"
            )


            criteria = result.get(
                "criteria",
                []
            )


            if not criteria:

                st.info(
                    "No policy criteria were available "
                    "for this request."
                )


            else:

                left_criteria, right_criteria = st.columns(
                    2
                )


                midpoint = (
                    len(criteria) + 1
                ) // 2


                # ------------------------------------------------
                # LEFT CRITERIA
                # ------------------------------------------------

                with left_criteria:

                    for criterion in criteria[
                        :midpoint
                    ]:

                        status = criterion.get(
                            "status",
                            "UNKNOWN"
                        )

                        name = criterion.get(
                            "criterion",
                            "Criterion"
                        )

                        reason = criterion.get(
                            "reason",
                            ""
                        )


                        if status == "PASSED":

                            st.success(
                                f"✓ {name}"
                            )

                        elif status == "FAILED":

                            st.error(
                                f"✗ {name}"
                            )

                        elif status == "NOT_APPLICABLE":

                            st.info(
                                f"— {name}"
                            )

                        else:

                            st.warning(
                                f"? {name}"
                            )


                        if reason:

                            st.caption(
                                reason
                            )


                # ------------------------------------------------
                # RIGHT CRITERIA
                # ------------------------------------------------

                with right_criteria:

                    for criterion in criteria[
                        midpoint:
                    ]:

                        status = criterion.get(
                            "status",
                            "UNKNOWN"
                        )

                        name = criterion.get(
                            "criterion",
                            "Criterion"
                        )

                        reason = criterion.get(
                            "reason",
                            ""
                        )


                        if status == "PASSED":

                            st.success(
                                f"✓ {name}"
                            )

                        elif status == "FAILED":

                            st.error(
                                f"✗ {name}"
                            )

                        elif status == "NOT_APPLICABLE":

                            st.info(
                                f"— {name}"
                            )

                        else:

                            st.warning(
                                f"? {name}"
                            )


                        if reason:

                            st.caption(
                                reason
                            )


    # ========================================================
    # NORMALIZED PATIENT DATA
    # ========================================================

    with st.expander(
        "View normalized patient data"
    ):

        st.json(
            patient
        )


    # ========================================================
    # POLICY USED
    # ========================================================

    policy_used = result.get(
        "policy"
    )

    if policy_used:

        with st.expander(
            "View applicable policy"
        ):

            st.json(
                policy_used
            )
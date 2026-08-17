from pathlib import Path

import streamlit as st

from src.pdf_extractor import extract_text_from_pdf
from src.patient_parser import parse_patient, validate_patient
from src.normalizer import normalize_patient
from src.policy_matcher import load_policies
from src.decision import load_no_prior_auth, process_decision


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
        border: none !important;
    }

    .stButton > button[kind="primary"] {
        background: var(--brand) !important;
        color: white !important;
        box-shadow:
            0 7px 18px rgba(20, 99, 86, 0.18);
    }

    .stButton > button[kind="primary"]:hover {
        background: #105448 !important;

        box-shadow:
            0 11px 25px rgba(20, 99, 86, 0.24);
    }


    /* ========================================================
       METRICS
       ======================================================== */

    [data-testid="stMetric"] {
        background: var(--surface);
        border: none !important;
        border-radius: 14px;
        padding: 16px;

        box-shadow:
            0 8px 25px rgba(27, 36, 48, 0.06);
    }

    [data-testid="stMetricLabel"] {
        font-family: "IBM Plex Sans", sans-serif !important;
        color: var(--muted) !important;
        font-size: 0.75rem !important;
        text-transform: uppercase;
        letter-spacing: 0.8px;
    }

    [data-testid="stMetricValue"] {
        font-family: "IBM Plex Mono", monospace !important;
        color: var(--ink) !important;
        font-size: 1rem !important;
    }


    /* ========================================================
       ALERTS
       ======================================================== */

    [data-testid="stAlert"] {
        border-radius: 12px !important;
    }


    /* ========================================================
       EXPANDERS
       ======================================================== */

    [data-testid="stExpander"] {
        background: var(--surface);
        border: none !important;
        border-radius: 14px !important;

        box-shadow:
            0 8px 25px rgba(27, 36, 48, 0.05);
    }


    /* ========================================================
       DIVIDERS
       ======================================================== */

    hr {
        border-color: var(--line) !important;
    }


    /* ========================================================
       ANIMATIONS
       ======================================================== */

    @keyframes fadeUp {

        from {
            opacity: 0;
            transform: translateY(8px);
        }

        to {
            opacity: 1;
            transform: translateY(0);
        }

    }

    @keyframes stampIn {

        0% {
            opacity: 0;
            transform:
                scale(1.35)
                rotate(-7deg);
        }

        65% {
            opacity: 1;
            transform:
                scale(0.96)
                rotate(-1deg);
        }

        100% {
            opacity: 1;
            transform:
                scale(1)
                rotate(-2deg);
        }

    }

    .stMarkdown,
    [data-testid="stMetric"],
    [data-testid="stFileUploader"],
    .stButton {
        animation:
            fadeUp 350ms ease-out both;
    }


    /* ========================================================
       DECISION STAMPS
       ======================================================== */

    .decision-stamp-container {
        padding: 55px 10px;
        text-align: center;
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

    if value is None:
        return default

    value = str(value).strip()

    if not value:
        return default

    return value.title()


def safe_upper(value, default="Not provided"):

    if value is None:
        return default

    value = str(value).strip()

    if not value:
        return default

    return value.upper()


def safe_display(value, default="Not provided"):

    if value is None:
        return default

    if isinstance(value, str) and not value.strip():
        return default

    return str(value)


# ============================================================
# GET CRITERIA FROM RESULT
# ============================================================

def get_criteria(result):
    """
    The current rule_engine.py returns evaluated criteria
    under the key 'results'.

    Older/newer versions may use 'criteria'.

    Support both so the UI never incorrectly shows
    zero criteria.
    """

    if not isinstance(result, dict):
        return []

    criteria = result.get("criteria")

    if isinstance(criteria, list):
        return criteria

    results = result.get("results")

    if isinstance(results, list):
        return results

    return []


# ============================================================
# GET APPLIED POLICY
# ============================================================

def get_policy_name(result):

    if not isinstance(result, dict):
        return None

    return (
        result.get("policy_name")
        or result.get("applied_policy_name")
    )


def get_policy_id(result):

    if not isinstance(result, dict):
        return None

    return (
        result.get("policy_id")
        or result.get("applied_policy_id")
    )


# ============================================================
# COUNT CRITERIA
# ============================================================

def count_criteria(criteria):

    passed = 0
    failed = 0
    not_applicable = 0
    other = 0

    for criterion in criteria:

        status = str(
            criterion.get(
                "status",
                ""
            )
        ).upper()

        if status == "PASSED":
            passed += 1

        elif status == "FAILED":
            failed += 1

        elif status == "NOT_APPLICABLE":
            not_applicable += 1

        else:
            other += 1

    return (
        passed,
        failed,
        not_applicable,
        other
    )


# ============================================================
# RENDER CRITERION
# ============================================================

def render_criterion(criterion):

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

    status = str(
        status
    ).upper()

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


# ============================================================
# RENDER ALL CRITERIA
# ============================================================

def render_criteria(criteria):

    if not criteria:

        st.info(
            "No policy criteria were returned "
            "by the policy evaluation engine."
        )

        return

    left_criteria, right_criteria = st.columns(
        2
    )

    midpoint = (
        len(criteria) + 1
    ) // 2

    with left_criteria:

        for criterion in criteria[
            :midpoint
        ]:

            render_criterion(
                criterion
            )

    with right_criteria:

        for criterion in criteria[
            midpoint:
        ]:

            render_criterion(
                criterion
            )


# ============================================================
# UPLOAD PAGE
# ============================================================

if st.session_state.page == "upload":

    st.title("🏥 PriorAuth AI")

    st.caption(
        "Intelligent Prior Authorization Decision Support"
    )

    st.divider()

    st.title(
        "Prior Authorization Review"
    )

    st.write(
        "Upload a patient record and let the policy engine "
        "evaluate the request against the applicable "
        "coverage requirements."
    )

    st.write("")

    with st.container(border=True):

        st.subheader(
            "Patient Record"
        )

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
                    # 2. PATIENT PARSING
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

                    patient = normalize_patient(
                        patient
                    )


                    # ==================================================
                    # 4. VALIDATION
                    # ==================================================

                    validation = validate_patient(
                        patient
                    )

                    # --------------------------------------------------
                    # Your validate_patient() versions have used both
                    # "missing_fields" and "errors".
                    # Support both.
                    # --------------------------------------------------

                    missing_fields = validation.get(
                        "missing_fields",
                        []
                    )

                    if not missing_fields:

                        missing_fields = validation.get(
                            "errors",
                            []
                        )

                    st.session_state.missing_fields = (
                        missing_fields
                    )


                    # ==================================================
                    # 5. LOAD POLICIES
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
                    # 6. POLICY EVALUATION
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
                    # 7. STORE RESULT
                    # ==================================================

                    st.session_state.patient = (
                        patient
                    )

                    st.session_state.result = (
                        result
                    )

                    st.session_state.page = (
                        "decision"
                    )

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

    if st.button(
        "← New Request"
    ):

        st.session_state.page = (
            "upload"
        )

        st.session_state.patient = None

        st.session_state.result = None

        st.session_state.missing_fields = []

        st.rerun()


    # ========================================================
    # HEADER
    # ========================================================

    st.title(
        "🏥 PriorAuth AI"
    )

    st.caption(
        "Authorization Decision"
    )

    st.divider()


    # ========================================================
    # REQUEST SUMMARY
    # ========================================================

    st.subheader(
        "Request Summary"
    )

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

            readable_fields = []

            for field in missing_fields:

                field = str(
                    field
                )

                readable_fields.append(
                    field.replace(
                        "_",
                        " "
                    ).title()
                )

            st.caption(
                "Missing fields: "
                + ", ".join(
                    readable_fields
                )
            )


    # ========================================================
    # DECISION
    # ========================================================

    decision = result.get(
        "decision",
        "MANUAL REVIEW"
    )

    decision = str(
        decision
    ).upper()


    # ========================================================
    # GET ACTUAL CRITERIA
    #
    # IMPORTANT:
    #
    # rule_engine.py currently returns:
    #
    #     "results": [...]
    #
    # NOT:
    #
    #     "criteria": [...]
    #
    # get_criteria() handles both.
    # ========================================================

    criteria = get_criteria(
        result
    )


    # ========================================================
    # COUNT RESULTS
    # ========================================================

    (
        passed_count,
        failed_count,
        not_applicable_count,
        other_count
    ) = count_criteria(
        criteria
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

            st.subheader(
                "Final Decision"
            )


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
                    "The request does not satisfy "
                    "one or more policy requirements."
                )


            elif (
                decision == "MANUAL REVIEW"
                or decision == "MANUAL_REVIEW"
            ):

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
                    "The request requires "
                    "additional review."
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
    # RIGHT: DECISION EXPLANATION
    # ========================================================

    with reason_col:

        with st.container(border=True):

            st.subheader(
                "Decision Explanation"
            )


            # ====================================================
            # APPROVED
            # ====================================================

            if decision == "APPROVED":

                if criteria:

                    st.write(
                        f"The request satisfied "
                        f"**{passed_count}** "
                        "policy requirement(s)."
                    )

                    if not_applicable_count:

                        st.caption(
                            f"{not_applicable_count} "
                            "criterion/criteria were "
                            "not applicable."
                        )

                else:

                    st.write(
                        "The request was approved, "
                        "but no individual criteria "
                        "were returned by the evaluation engine."
                    )


            # ====================================================
            # DENIED
            # ====================================================

            elif decision == "DENIED":

                if criteria:

                    st.write(
                        f"The request failed "
                        f"**{failed_count}** "
                        "policy requirement(s)."
                    )

                else:

                    st.write(
                        "The request was denied, "
                        "but no individual criteria "
                        "were returned by the evaluation engine."
                    )


            # ====================================================
            # MANUAL REVIEW
            # ====================================================

            elif (
                decision == "MANUAL REVIEW"
                or decision == "MANUAL_REVIEW"
            ):

                st.write(
                    result.get(
                        "reason",
                        "The request requires "
                        "manual review."
                    )
                )


            # ====================================================
            # NO PA
            # ====================================================

            elif decision == "NO_PRIOR_AUTH_REQUIRED":

                st.write(
                    result.get(
                        "reason",
                        "Prior authorization is "
                        "not required for this service."
                    )
                )


            else:

                st.write(
                    result.get(
                        "reason",
                        "Policy evaluation completed."
                    )
                )


    # ========================================================
    # APPLIED POLICY
    # ========================================================

    policy_id = get_policy_id(
        result
    )

    policy_name = get_policy_name(
        result
    )


    if policy_id or policy_name:

        st.write("")

        with st.container(border=True):

            st.subheader(
                "Applied Policy"
            )

            policy_col1, policy_col2 = st.columns(
                2
            )

            with policy_col1:

                st.caption(
                    "POLICY"
                )

                st.write(
                    safe_display(
                        policy_name
                    )
                )

            with policy_col2:

                st.caption(
                    "POLICY ID"
                )

                st.code(
                    safe_display(
                        policy_id
                    ),
                    language=None
                )


    # ========================================================
    # APPROVED POLICY SUMMARY
    # ========================================================

    if decision == "APPROVED":

        st.write("")

        with st.container(border=True):

            st.subheader(
                "Authorization Summary"
            )

            summary_col1, summary_col2 = st.columns(
                2
            )

            with summary_col1:

                st.metric(
                    "Criteria Satisfied",
                    passed_count
                )

            with summary_col2:

                st.metric(
                    "Criteria Evaluated",
                    len(criteria)
                )


            # ------------------------------------------------
            # OPTION TO VIEW CRITERIA
            # ------------------------------------------------

            if criteria:

                with st.expander(
                    "View satisfied policy criteria"
                ):

                    render_criteria(
                        criteria
                    )

            else:

                st.warning(
                    "The authorization was approved, "
                    "but the decision engine did not "
                    "return its individual criteria."
                )


    # ========================================================
    # DENIAL REASONS
    # ========================================================

    if decision == "DENIED":

        failed_criteria = [

            criterion

            for criterion in criteria

            if str(
                criterion.get(
                    "status",
                    ""
                )
            ).upper() == "FAILED"

        ]


        if failed_criteria:

            st.write("")

            with st.container(border=True):

                st.subheader(
                    "Reasons for Denial"
                )

                for criterion in failed_criteria:

                    name = criterion.get(
                        "criterion",
                        "Criterion"
                    )

                    reason = criterion.get(
                        "reason",
                        "Requirement was not satisfied."
                    )

                    st.error(
                        f"**{name}** — {reason}"
                    )


        # ----------------------------------------------------
        # Full criteria available as expandable section
        # ----------------------------------------------------

        if criteria:

            with st.expander(
                "View all policy criteria"
            ):

                render_criteria(
                    criteria
                )


    # ========================================================
    # POLICY EVALUATION NOTICE
    # ========================================================

    if criteria:

        st.write("")

        st.info(
            "Policy criteria were evaluated against "
            "the submitted patient information."
        )


    # ========================================================
    # DEBUG / AUDIT DETAILS
    #
    # Useful during development, but hidden by default.
    # ========================================================

    with st.expander(
        "View evaluation details"
    ):

        st.json(
            {
                "decision": decision,
                "policy_id": policy_id,
                "policy_name": policy_name,
                "criteria_count": len(criteria),
                "passed_count": passed_count,
                "failed_count": failed_count,
                "not_applicable_count": (
                    not_applicable_count
                ),
            }
        )


    # ========================================================
    # PATIENT DATA
    # ========================================================

    st.write("")

    with st.expander(
        "View normalized patient data"
    ):

        st.json(
            patient
        )
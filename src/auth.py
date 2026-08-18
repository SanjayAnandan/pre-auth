"""
src/auth.py - Clinical SaaS Authentication System & Session Management
Provides user profiles, role-based access, authentication verification,
user registration (Sign Up), and a high-end login portal for PREAUTH.
"""

import streamlit as st
import textwrap
from typing import Dict, Any, Optional

# Default clinical user profiles with credentials, roles, and avatar metadata
DEFAULT_USERS: Dict[str, Dict[str, Any]] = {
    "reviewer@preauth.med": {
        "email": "reviewer@preauth.med",
        "username": "reviewer",
        "password": "password123",
        "name": "Alex Vance, RN",
        "role": "Senior Clinical Reviewer",
        "department": "Prior Auth Operations",
        "initials": "AV",
        "color": "#0f766e", # Teal
        "badge": "Clinical Reviewer",
    },
    "cmo@preauth.med": {
        "email": "cmo@preauth.med",
        "username": "cmo",
        "password": "password123",
        "name": "Dr. Sarah Jenkins, MD",
        "role": "Chief Medical Officer",
        "department": "Medical Affairs",
        "initials": "SJ",
        "color": "#1e3a8a", # Indigo/Navy
        "badge": "CMO / Approver",
    },
    "specialist@preauth.med": {
        "email": "specialist@preauth.med",
        "username": "specialist",
        "password": "password123",
        "name": "Maya Patel, CPC",
        "role": "Prior Auth Specialist",
        "department": "Intake & Verification",
        "initials": "MP",
        "color": "#0369a1", # Sky Blue
        "badge": "Auth Specialist",
    },
    "auditor@preauth.med": {
        "email": "auditor@preauth.med",
        "username": "auditor",
        "password": "password123",
        "name": "Jordan Reed, CHC",
        "role": "Compliance & Audit Manager",
        "department": "Regulatory Assurance",
        "initials": "JR",
        "color": "#b45309", # Amber/Gold
        "badge": "Compliance Auditor",
    },
}


def init_auth_session():
    """Initializes session state variables for user authentication and user store."""
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False

    if "user" not in st.session_state:
        st.session_state.user = None

    if "custom_users" not in st.session_state:
        st.session_state.custom_users = {}


def get_all_users() -> Dict[str, Dict[str, Any]]:
    """Returns combined map of default users, Supabase DB users, and session custom users."""
    users = dict(DEFAULT_USERS)

    # Load users persisted in Supabase database
    try:
        from src.database import get_user_profiles_from_db
        db_users = get_user_profiles_from_db()
        for u in db_users:
            if u.get("email"):
                users[u["email"].lower()] = u
    except Exception:
        pass

    if "custom_users" in st.session_state:
        users.update(st.session_state.custom_users)

    return users


def verify_credentials(username_or_email: str, password: str) -> Optional[Dict[str, Any]]:
    """Validates login credentials against all registered user accounts."""
    all_users = get_all_users()
    key = username_or_email.strip().lower()

    # Direct match by email key
    if key in all_users and all_users[key]["password"] == password:
        return all_users[key]

    # Match by username property
    for user_info in all_users.values():
        u_name = user_info.get("username", "").lower()
        u_email = user_info.get("email", "").lower()
        if (u_name == key or u_email == key) and user_info["password"] == password:
            return user_info

    return None


def register_new_user(name: str, email: str, password: str, role: str) -> Dict[str, Any]:
    """Registers a new clinical user account into session memory and Supabase DB."""
    clean_email = email.strip().lower()
    clean_username = clean_email.split("@")[0]

    # Compute initials
    name_parts = [p for p in name.replace("Dr.", "").replace("MD", "").replace("RN", "").replace("CPC", "").replace("CHC", "").strip().split() if p]
    if len(name_parts) >= 2:
        initials = (name_parts[0][0] + name_parts[-1][0]).upper()
    elif len(name_parts) == 1:
        initials = name_parts[0][:2].upper()
    else:
        initials = "CU"

    # Role configuration mapping
    role_meta = {
        "Senior Clinical Reviewer": {"dept": "Prior Auth Operations", "badge": "Clinical Reviewer", "color": "#0f766e"},
        "Chief Medical Officer": {"dept": "Medical Affairs", "badge": "CMO / Approver", "color": "#1e3a8a"},
        "Prior Auth Specialist": {"dept": "Intake & Verification", "badge": "Auth Specialist", "color": "#0369a1"},
        "Compliance & Audit Manager": {"dept": "Regulatory Assurance", "badge": "Compliance Auditor", "color": "#b45309"},
        "Attending Physician / Reviewer": {"dept": "Clinical Practice", "badge": "Physician Reviewer", "color": "#0d9488"},
    }

    meta = role_meta.get(role, {"dept": "Clinical Operations", "badge": role, "color": "#0d9488"})

    new_user = {
        "email": clean_email,
        "username": clean_username,
        "password": password,
        "name": name.strip(),
        "role": role,
        "department": meta["dept"],
        "initials": initials,
        "color": meta["color"],
        "badge": meta["badge"],
    }

    if "custom_users" not in st.session_state:
        st.session_state.custom_users = {}

    st.session_state.custom_users[clean_email] = new_user

    # Persist to Supabase PostgreSQL database table 'user_profiles'
    try:
        from src.database import save_user_profile
        save_user_profile(new_user)
    except Exception as db_err:
        st.warning(f"Account active in session. DB notice: {db_err}")

    return new_user


def login_user(user_info: Dict[str, Any]):
    """Sets active logged-in user in session state and triggers UI refresh."""
    st.session_state.authenticated = True
    st.session_state.user = user_info
    st.rerun()


def logout():
    """Clears user authentication and resets navigation state."""
    st.session_state.authenticated = False
    st.session_state.user = None
    st.session_state.active_case = None
    st.session_state.nav_page = "dashboard"
    st.rerun()


def clean_html(html_str: str) -> str:
    """Strips line breaks and indentation to prevent Streamlit markdown code block parsing."""
    return " ".join(line.strip() for line in html_str.splitlines())


def render_login_page():
    """Renders a high-end, clinical SaaS portal with Sign In and Sign Up options."""
    st.markdown(
        clean_html("""
        <style>
        .login-hero-container {
            max-width: 1040px;
            margin: 20px auto 40px auto;
            background: #ffffff;
            border: 1px solid #e2e8f0;
            border-radius: 16px;
            box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.05), 0 8px 10px -6px rgba(0, 0, 0, 0.03);
            overflow: hidden;
            display: flex;
            flex-direction: row;
        }

        .login-left-panel {
            flex: 1.1;
            background: linear-gradient(135deg, #0f172a 0%, #0f766e 100%);
            color: #ffffff;
            padding: 44px 40px;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
            position: relative;
        }

        .login-left-panel::after {
            content: '';
            position: absolute;
            top: 0; right: 0; bottom: 0; left: 0;
            background: radial-gradient(circle at top right, rgba(20, 184, 166, 0.25), transparent 60%);
            pointer-events: none;
        }

        .login-right-panel {
            flex: 1;
            padding: 34px 30px;
            background: #ffffff;
            display: flex;
            flex-direction: column;
            justify-content: center;
        }

        .demo-login-divider {
            display: flex;
            align-items: center;
            text-align: center;
            color: #94a3b8;
            font-size: 11px;
            font-weight: 600;
            letter-spacing: 0.05em;
            text-transform: uppercase;
            margin: 18px 0 14px 0;
        }

        .demo-login-divider::before, .demo-login-divider::after {
            content: '';
            flex: 1;
            border-bottom: 1px solid #e2e8f0;
        }

        .demo-login-divider::before { margin-right: 12px; }
        .demo-login-divider::after { margin-left: 12px; }
        </style>
        """),
        unsafe_allow_html=True
    )

    # Main layout columns
    col_left, col_right = st.columns([1.1, 1])

    with col_left:
        st.markdown(
            clean_html("""
            <div style="background: linear-gradient(135deg, #0f172a 0%, #0f766e 100%); color: white; padding: 38px 32px; border-radius: 16px; min-height: 540px; display: flex; flex-direction: column; justify-content: space-between; box-shadow: 0 10px 25px -5px rgba(15, 118, 110, 0.3);">
                <div>
                    <div style="display: flex; align-items: center; gap: 10px;">
                        <div style="width: 38px; height: 38px; background: rgba(255,255,255,0.15); border: 1px solid rgba(255,255,255,0.3); border-radius: 8px; display: flex; align-items: center; justify-content: center; font-weight: 700; font-size: 20px;">✚</div>
                        <span style="font-size: 22px; font-weight: 800; letter-spacing: -0.02em;">PREAUTH</span>
                    </div>
                    
                    <h2 style="font-size: 24px; font-weight: 700; margin-top: 24px; margin-bottom: 12px; line-height: 1.3; color: #ffffff;">
                        Autonomous Prior Authorization Intelligence
                    </h2>
                    <p style="font-size: 13.5px; color: #cbd5e1; line-height: 1.6; margin-bottom: 24px;">
                        Privacy-first AI intake, identity verification, ML risk scoring, and deterministic clinical policy decisioning engine.
                    </p>
                    
                    <div style="display: flex; flex-direction: column; gap: 12px; margin-bottom: 24px;">
                        <div style="display: flex; align-items: center; gap: 10px; font-size: 13px; color: #e2e8f0;">
                            <span style="color: #2dd4bf; font-weight: 700;">✓</span> HIPAA-Compliant De-identification Boundary
                        </div>
                        <div style="display: flex; align-items: center; gap: 10px; font-size: 13px; color: #e2e8f0;">
                            <span style="color: #2dd4bf; font-weight: 700;">✓</span> Real-Time Supabase PostgreSQL Persistence
                        </div>
                        <div style="display: flex; align-items: center; gap: 10px; font-size: 13px; color: #e2e8f0;">
                            <span style="color: #2dd4bf; font-weight: 700;">✓</span> CPT / HCPCS & ICD-10 Policy Rule Engine
                        </div>
                        <div style="display: flex; align-items: center; gap: 10px; font-size: 13px; color: #e2e8f0;">
                            <span style="color: #2dd4bf; font-weight: 700;">✓</span> Complete Audit & Decision Traceability
                        </div>
                    </div>
                </div>

                <div style="background: rgba(255,255,255,0.08); border: 1px solid rgba(255,255,255,0.15); border-radius: 10px; padding: 12px 16px; font-size: 12px; color: #94a3b8; display: flex; align-items: center; justify-content: space-between;">
                    <span>🔒 256-Bit Encrypted Portal</span>
                    <span style="color: #2dd4bf; font-weight: 600;">System Online</span>
                </div>
            </div>
            """),
            unsafe_allow_html=True
        )

    with col_right:
        # Tab selection for Sign In vs Sign Up
        tab_signin, tab_signup = st.tabs(["🔑  Sign In", "📝  Create Account (Sign Up)"])

        # -------------------------------------------------------------
        # TAB 1: SIGN IN
        # -------------------------------------------------------------
        with tab_signin:
            st.markdown(
                clean_html("""
                <div style="padding: 10px 0;">
                    <h3 style="font-size: 20px; font-weight: 700; color: #0f172a; margin: 0 0 4px 0;">Clinical Portal Sign In</h3>
                    <p style="font-size: 12.5px; color: #64748b; margin: 0 0 16px 0;">Enter your clinical credentials to access authorization management.</p>
                </div>
                """),
                unsafe_allow_html=True
            )

            with st.form("login_form", clear_on_submit=False):
                username_or_email = st.text_input(
                    "Username or Email",
                    placeholder="e.g. reviewer@preauth.med or reviewer",
                    key="login_email_input"
                )
                password = st.text_input(
                    "Password",
                    type="password",
                    placeholder="••••••••••••",
                    key="login_password_input"
                )
                
                remember_me = st.checkbox("Remember this session", value=True)
                submit_btn = st.form_submit_button("Sign In to Portal", use_container_width=True, type="primary")

                if submit_btn:
                    if not username_or_email or not password:
                        st.error("Please enter both username/email and password.")
                    else:
                        matched_user = verify_credentials(username_or_email, password)
                        if matched_user:
                            st.success(f"Welcome back, {matched_user['name']}!")
                            login_user(matched_user)
                        else:
                            st.error("Invalid credentials. Please check your username/email or password.")

            st.markdown(
                """
                <div class="demo-login-divider">
                    <span>OR ONE-CLICK DEMO SIGN IN</span>
                </div>
                """,
                unsafe_allow_html=True
            )

            st.caption("Select a pre-configured clinical profile:")
            btn_col1, btn_col2 = st.columns(2)
            with btn_col1:
                if st.button("👩‍⚕️ Clinical Reviewer", key="demo_reviewer_btn", use_container_width=True):
                    login_user(DEFAULT_USERS["reviewer@preauth.med"])
                if st.button("📑 Auth Specialist", key="demo_specialist_btn", use_container_width=True):
                    login_user(DEFAULT_USERS["specialist@preauth.med"])

            with btn_col2:
                if st.button("🩺 Chief Medical Officer", key="demo_cmo_btn", use_container_width=True):
                    login_user(DEFAULT_USERS["cmo@preauth.med"])
                if st.button("⚖️ Compliance Auditor", key="demo_auditor_btn", use_container_width=True):
                    login_user(DEFAULT_USERS["auditor@preauth.med"])

        # -------------------------------------------------------------
        # TAB 2: SIGN UP
        # -------------------------------------------------------------
        with tab_signup:
            st.markdown(
                clean_html("""
                <div style="padding: 10px 0;">
                    <h3 style="font-size: 20px; font-weight: 700; color: #0f172a; margin: 0 0 4px 0;">Register New Account</h3>
                    <p style="font-size: 12.5px; color: #64748b; margin: 0 0 16px 0;">Create a new clinical profile to evaluate prior authorizations.</p>
                </div>
                """),
                unsafe_allow_html=True
            )

            with st.form("signup_form", clear_on_submit=False):
                reg_name = st.text_input(
                    "Full Name & Title",
                    placeholder="e.g. Dr. Jane Doe, MD",
                    key="signup_name_input"
                )
                
                reg_role = st.selectbox(
                    "Clinical Role",
                    options=[
                        "Senior Clinical Reviewer",
                        "Chief Medical Officer",
                        "Prior Auth Specialist",
                        "Compliance & Audit Manager",
                        "Attending Physician / Reviewer",
                    ],
                    key="signup_role_select"
                )

                reg_email = st.text_input(
                    "Clinical Email Address",
                    placeholder="e.g. jane.doe@preauth.med",
                    key="signup_email_input"
                )

                col_p1, col_p2 = st.columns(2)
                with col_p1:
                    reg_pass1 = st.text_input(
                        "Password",
                        type="password",
                        placeholder="••••••••••••",
                        key="signup_pass1_input"
                    )
                with col_p2:
                    reg_pass2 = st.text_input(
                        "Confirm Password",
                        type="password",
                        placeholder="••••••••••••",
                        key="signup_pass2_input"
                    )

                signup_submit = st.form_submit_button("Create Account & Sign In", use_container_width=True, type="primary")

                if signup_submit:
                    all_users = get_all_users()
                    clean_email = reg_email.strip().lower()

                    if not reg_name or not reg_email or not reg_pass1:
                        st.error("Please fill in all required registration fields.")
                    elif reg_pass1 != reg_pass2:
                        st.error("Passwords do not match. Please re-enter your password.")
                    elif len(reg_pass1) < 6:
                        st.error("Password must be at least 6 characters long.")
                    elif clean_email in all_users:
                        st.error("An account with this email address is already registered.")
                    else:
                        new_user = register_new_user(reg_name, reg_email, reg_pass1, reg_role)
                        st.success(f"Account created successfully for {new_user['name']}!")
                        login_user(new_user)

"""
src/auth.py - Clinical SaaS Authentication System & Session Management
Provides user profiles, role-based access, Supabase Auth integration,
user registration (Sign Up), and an enterprise clinical login portal for PREAUTH.
"""

import logging
import os
import streamlit as st
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)

# Initial Clinical Profiles metadata (used for database seeding and user profile enrichment)
INITIAL_CLINICAL_PROFILES: Dict[str, Dict[str, Any]] = {
    "reviewer@preauth.med": {
        "email": "reviewer@preauth.med",
        "username": "reviewer",
        "name": "Alex Vance, RN",
        "role": "Senior Clinical Reviewer",
        "department": "Prior Auth Operations",
        "initials": "AV",
        "color": "#0f766e",
        "badge": "Clinical Reviewer",
    },
    "cmo@preauth.med": {
        "email": "cmo@preauth.med",
        "username": "cmo",
        "name": "Dr. Sarah Jenkins, MD",
        "role": "Chief Medical Officer",
        "department": "Medical Affairs",
        "initials": "SJ",
        "color": "#1e3a8a",
        "badge": "CMO / Approver",
    },
    "specialist@preauth.med": {
        "email": "specialist@preauth.med",
        "username": "specialist",
        "name": "Maya Patel, CPC",
        "role": "Prior Auth Specialist",
        "department": "Intake & Verification",
        "initials": "MP",
        "color": "#0369a1",
        "badge": "Auth Specialist",
    },
    "auditor@preauth.med": {
        "email": "auditor@preauth.med",
        "username": "auditor",
        "name": "Jordan Reed, CHC",
        "role": "Compliance & Audit Manager",
        "department": "Regulatory Assurance",
        "initials": "JR",
        "color": "#b45309",
        "badge": "Compliance Auditor",
    },
}

# Initial Clinical Profiles dictionary (used for profile display metadata and seeding)
DEFAULT_USERS: Dict[str, Dict[str, Any]] = {
    email: dict(prof)
    for email, prof in INITIAL_CLINICAL_PROFILES.items()
}


def init_auth_session():
    """Initializes session state variables for user authentication and user store."""
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False

    if "user" not in st.session_state:
        st.session_state.user = None

    if "custom_users" not in st.session_state:
        st.session_state.custom_users = {}

    # Seed Supabase DB user_profiles if connected
    try:
        from src.database import seed_initial_user_profiles_to_db
        seed_initial_user_profiles_to_db()
    except Exception:
        pass


def get_all_user_profiles() -> Dict[str, Dict[str, Any]]:
    """Returns map of user profiles from Supabase database, session custom users, and initial profiles."""
    profiles = dict(INITIAL_CLINICAL_PROFILES)

    # Load user profiles from Supabase database
    try:
        from src.database import get_user_profiles_from_db
        db_users = get_user_profiles_from_db()
        for u in db_users:
            if u.get("email"):
                profiles[u["email"].lower()] = u
    except Exception as e:
        logger.debug(f"Note: Error loading profiles from DB: {e}")

    if "custom_users" in st.session_state:
        for email, u in st.session_state.custom_users.items():
            profiles[email.lower()] = u

    return profiles


# Alias for backward compatibility
get_all_users = get_all_user_profiles


def verify_credentials(username_or_email: str, password: str) -> Optional[Dict[str, Any]]:
    """
    Validates login credentials via Supabase Auth and loads user's profile from user_profiles table.
    - Resolves username to email via user_profiles lookup if necessary.
    - Authenticates via Supabase Auth sign_in_with_password.
    - Resolves/links profile via get_or_link_user_profile.
    - Differentiates invalid credentials, unconfirmed email, and profile/service errors.
    """
    st.session_state.last_auth_error = None

    if not username_or_email or not password:
        return None

    input_key = username_or_email.strip()
    profiles = get_all_user_profiles()

    # 1. Resolve target email if username was provided
    target_email = input_key.lower()
    matched_profile = None

    if "@" not in input_key:
        found_match = False
        for p in profiles.values():
            if str(p.get("username", "")).lower() == input_key.lower() or str(p.get("email", "")).lower() == input_key.lower():
                target_email = str(p.get("email", input_key)).lower()
                matched_profile = p
                found_match = True
                break
        if not found_match:
            st.session_state.last_auth_error = "Invalid credentials. Please check your username/email or password."
            return None
    elif input_key.lower() in profiles:
        matched_profile = profiles[input_key.lower()]

    # 2. Authenticate via Supabase Auth ONLY
    try:
        from src.database import get_supabase_client, get_or_link_user_profile
        client = get_supabase_client()

        if client is not None:
            try:
                auth_resp = client.auth.sign_in_with_password({
                    "email": target_email,
                    "password": password
                })

                if auth_resp and auth_resp.user:
                    if hasattr(auth_resp, "session") and auth_resp.session:
                        st.session_state.supabase_session = auth_resp.session

                    auth_user = auth_resp.user
                    try:
                        meta = getattr(auth_user, "user_metadata", None) or {}
                        name_hint = meta.get("full_name") or meta.get("name") or (matched_profile.get("name") if matched_profile else None)
                        role_hint = meta.get("clinical_role") or meta.get("role") or (matched_profile.get("role") if matched_profile else None)
                        uname_hint = matched_profile.get("username") if matched_profile else None

                        profile = get_or_link_user_profile(
                            auth_user_id=auth_user.id,
                            email=auth_user.email or target_email,
                            name=name_hint,
                            role=role_hint,
                            username=uname_hint
                        )
                        if profile:
                            return profile
                        else:
                            st.session_state.last_auth_error = "Authentication succeeded, but your clinical profile could not be loaded. Please contact an administrator."
                            return None
                    except Exception as prof_err:
                        logger.error(f"Profile resolution error after Auth: {prof_err}")
                        st.session_state.last_auth_error = "Authentication succeeded, but your clinical profile could not be loaded. Please contact an administrator."
                        return None
            except Exception as auth_err:
                err_str = str(auth_err)
                logger.info(f"Supabase Auth sign-in result for {target_email}: {err_str}")
                if "Email not confirmed" in err_str or "email_not_confirmed" in err_str:
                    st.session_state.last_auth_error = "Email not confirmed. Please check your inbox and verify your email address before signing in."
                else:
                    st.session_state.last_auth_error = "Invalid credentials. Please check your username/email or password."
                return None
    except Exception as e:
        logger.debug(f"Supabase Auth client check notice: {e}")

    st.session_state.last_auth_error = "Invalid credentials. Please check your username/email or password."
    return None


def register_new_user(name: str, email: str, password: str, role: str) -> Optional[Dict[str, Any]]:
    """Registers a new clinical user account via Supabase Auth and creates/links user profile."""
    import uuid
    clean_email = email.strip().lower()
    clean_username = clean_email.split("@")[0]
    st.session_state.last_signup_error = None
    st.session_state.last_signup_message = None

    auth_user_id = None
    email_confirmation_required = False

    # Register in Supabase Auth if client available
    try:
        from src.database import get_supabase_client, get_or_link_user_profile
        client = get_supabase_client()
        if client is not None:
            try:
                redirect_url = os.environ.get("SUPABASE_REDIRECT_URL", "http://localhost:8501").strip()
                signUp_resp = client.auth.sign_up({
                    "email": clean_email,
                    "password": password,
                    "options": {
                        "email_redirect_to": redirect_url,
                        "data": {
                            "full_name": name.strip(),
                            "name": name.strip(),
                            "clinical_role": role,
                            "role": role,
                        }
                    }
                })
                if signUp_resp and signUp_resp.user:
                    auth_user_id = signUp_resp.user.id
                    if hasattr(signUp_resp, "session") and signUp_resp.session is None:
                        email_confirmation_required = True
            except Exception as su_err:
                err_str = str(su_err)
                logger.info(f"Supabase Auth sign_up notice: {err_str}")
                if "User already registered" in err_str or "already_exists" in err_str:
                    # Check if already registered in remote Auth: resolve or link existing profile
                    existing = get_or_link_user_profile(
                        auth_user_id=str(uuid.uuid4()),
                        email=clean_email,
                        name=name.strip(),
                        role=role,
                        username=clean_username
                    )
                    if existing:
                        return existing
                    st.session_state.last_signup_error = "An account with this email address is already registered."
                    return None

        # Resolve or link profile in user_profiles table
        profile = get_or_link_user_profile(
            auth_user_id=auth_user_id or str(uuid.uuid4()),
            email=clean_email,
            name=name.strip(),
            role=role,
            username=clean_username
        )
    except Exception as db_err:
        logger.warning(f"User profile save notice: {db_err}")
        profile = {
            "auth_id": auth_user_id or str(uuid.uuid4()),
            "email": clean_email,
            "username": clean_username,
            "full_name": name.strip(),
            "name": name.strip(),
            "clinical_role": role,
            "role": role,
            "department": "Clinical Operations",
            "initials": clean_email[:2].upper(),
            "badge_label": role,
            "badge": role,
            "color_hex": "#0f766e",
            "color": "#0f766e"
        }

    if email_confirmation_required:
        profile["email_confirmation_required"] = True
        st.session_state.last_signup_message = "Account created! Please check your email to confirm your account before signing in."

    # Also keep in session state custom_users with password for test fallback
    if "custom_users" not in st.session_state:
        st.session_state.custom_users = {}

    user_with_pass = dict(profile)
    user_with_pass["password"] = password
    st.session_state.custom_users[clean_email] = user_with_pass

    return profile


def login_user(user_profile: Dict[str, Any]):
    """Sets active logged-in user in session state and triggers UI refresh."""
    st.session_state.authenticated = True
    st.session_state.user = user_profile
    st.rerun()


def logout():
    """Clears user authentication and resets navigation & Streamlit session state."""
    try:
        from src.database import get_supabase_client
        client = get_supabase_client()
        if client is not None:
            client.auth.sign_out()
    except Exception as e:
        logger.debug(f"Supabase Auth sign_out notice: {e}")

    st.session_state.authenticated = False
    st.session_state.user = None
    st.session_state.supabase_session = None
    st.session_state.active_case = None
    st.session_state.nav_page = "dashboard"
    st.session_state.last_auth_error = None
    st.session_state.last_signup_error = None
    st.session_state.last_signup_message = None
    st.rerun()


def clean_html(html_str: str) -> str:
    """Strips line breaks and indentation to prevent Streamlit markdown code block parsing."""
    return " ".join(line.strip() for line in html_str.splitlines())


def render_login_page():
    """Renders a polished, enterprise clinical SaaS portal with Sign In and Sign Up options."""
    st.markdown(
        clean_html("""
        <style>
        /* Modern Healthcare SaaS Login Styling */
        div[data-testid="stTabs"] button[data-baseweb="tab"] {
            font-weight: 600 !important;
            font-size: 13.5px !important;
            color: #64748b !important;
            padding: 10px 16px !important;
            border-bottom: 2px solid transparent !important;
        }
        div[data-testid="stTabs"] button[data-baseweb="tab"][aria-selected="true"] {
            color: #2563eb !important;
            border-bottom-color: #2563eb !important;
            background: transparent !important;
        }
        </style>
        """),
        unsafe_allow_html=True
    )

    # Main layout columns aligned consistently
    col_left, col_right = st.columns([1.1, 1])

    with col_left:
        st.markdown(
            clean_html("""
            <div style="background: linear-gradient(135deg, #0f172a 0%, #0f766e 100%); color: white; padding: 36px 32px; border-radius: 12px; min-height: 530px; display: flex; flex-direction: column; justify-content: space-between; box-shadow: 0 10px 25px -5px rgba(15, 118, 110, 0.25); border: 1px solid #1e293b;">
                <div>
                    <div style="display: flex; align-items: center; gap: 10px;">
                        <div style="width: 36px; height: 36px; background: rgba(255,255,255,0.15); border: 1px solid rgba(255,255,255,0.3); border-radius: 8px; display: flex; align-items: center; justify-content: center;">
                            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#ffffff" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="5" x2="12" y2="19"></line><line x1="5" y1="12" x2="19" y2="12"></line></svg>
                        </div>
                        <span style="font-size: 22px; font-weight: 800; letter-spacing: -0.02em; color: #ffffff;">PREAUTH</span>
                    </div>
                    
                    <h2 style="font-size: 23px; font-weight: 700; margin-top: 24px; margin-bottom: 12px; line-height: 1.35; color: #ffffff; text-shadow: 0 1px 2px rgba(0,0,0,0.2);">
                        Autonomous Prior Authorization Intelligence
                    </h2>
                    <p style="font-size: 13.5px; color: #e2e8f0; line-height: 1.6; margin-bottom: 24px; font-weight: 400;">
                        Privacy-first AI intake, identity verification, ML risk scoring, and deterministic clinical policy decisioning engine.
                    </p>
                    
                    <div style="display: flex; flex-direction: column; gap: 14px; margin-bottom: 24px;">
                        <div style="display: flex; align-items: center; gap: 10px; font-size: 13px; color: #f1f5f9; font-weight: 500;">
                            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="#2dd4bf" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"></polyline></svg>
                            HIPAA-Compliant De-identification Boundary
                        </div>
                        <div style="display: flex; align-items: center; gap: 10px; font-size: 13px; color: #f1f5f9; font-weight: 500;">
                            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="#2dd4bf" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"></polyline></svg>
                            Real-Time Supabase PostgreSQL Persistence
                        </div>
                        <div style="display: flex; align-items: center; gap: 10px; font-size: 13px; color: #f1f5f9; font-weight: 500;">
                            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="#2dd4bf" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"></polyline></svg>
                            CPT / HCPCS & ICD-10 Policy Rule Engine
                        </div>
                        <div style="display: flex; align-items: center; gap: 10px; font-size: 13px; color: #f1f5f9; font-weight: 500;">
                            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="#2dd4bf" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"></polyline></svg>
                            Complete Audit & Decision Traceability
                        </div>
                    </div>
                </div>

                <div style="background: rgba(15,23,42,0.6); border: 1px solid rgba(255,255,255,0.15); border-radius: 8px; padding: 10px 14px; font-size: 12px; color: #cbd5e1; display: flex; align-items: center; justify-content: space-between;">
                    <div style="display: flex; align-items: center; gap: 6px;">
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#2dd4bf" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="11" width="18" height="11" rx="2" ry="2"></rect><path d="M7 11V7a5 5 0 0 1 10 0v4"></path></svg>
                        <span>256-Bit Encrypted Portal</span>
                    </div>
                    <span style="color: #2dd4bf; font-weight: 600;">System Online</span>
                </div>
            </div>
            """),
            unsafe_allow_html=True
        )

    with col_right:
        tab_signin, tab_signup = st.tabs(["Sign In", "Create Account"])

        # -------------------------------------------------------------
        # TAB 1: SIGN IN
        # -------------------------------------------------------------
        with tab_signin:
            st.markdown(
                clean_html("""
                <div style="padding: 6px 0 14px 0;">
                    <h3 style="font-size: 20px; font-weight: 700; color: #0f172a; margin: 0 0 4px 0;">Clinical Portal Sign In</h3>
                    <p style="font-size: 12.5px; color: #64748b; margin: 0;">Enter your clinical credentials to access authorization management.</p>
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
                            err_msg = st.session_state.get("last_auth_error") or "Invalid credentials. Please check your username/email or password."
                            st.error(err_msg)

        # -------------------------------------------------------------
        # TAB 2: SIGN UP
        # -------------------------------------------------------------
        with tab_signup:
            st.markdown(
                clean_html("""
                <div style="padding: 6px 0 14px 0;">
                    <h3 style="font-size: 20px; font-weight: 700; color: #0f172a; margin: 0 0 4px 0;">Register New Account</h3>
                    <p style="font-size: 12.5px; color: #64748b; margin: 0;">Create a new clinical profile to evaluate prior authorizations.</p>
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
                    clean_email = reg_email.strip().lower()

                    if not reg_name or not reg_email or not reg_pass1:
                        st.error("Please fill in all required registration fields.")
                    elif reg_pass1 != reg_pass2:
                        st.error("Passwords do not match. Please re-enter your password.")
                    elif len(reg_pass1) < 6:
                        st.error("Password must be at least 6 characters long.")
                    else:
                        new_user = register_new_user(reg_name, reg_email, reg_pass1, reg_role)
                        if new_user:
                            if new_user.get("email_confirmation_required"):
                                st.info(st.session_state.get("last_signup_message") or "Account created! Please check your email to confirm your account before signing in.")
                            else:
                                st.success(f"Account created successfully for {new_user['name']}!")
                                login_user(new_user)
                        else:
                            err_msg = st.session_state.get("last_signup_error") or "Could not create account. Please try again."
                            st.error(err_msg)

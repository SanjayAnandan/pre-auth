"""
tests/test_auth.py

Comprehensive Authentication & Profile Persistence Test Suite.
Verifies Supabase Auth, credential verification, profile linking, signup, login, logout, and error handling.
"""

import unittest
from unittest.mock import patch, MagicMock
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.auth import (
    DEFAULT_USERS,
    init_auth_session,
    get_all_users,
    verify_credentials,
    register_new_user,
    login_user,
    logout,
)
from src.database import get_or_link_user_profile, save_user_profile, get_user_profile_by_email


class TestAuthModule(unittest.TestCase):

    def setUp(self):
        class SessionStateMock(dict):
            def __getattr__(self, key):
                return self.get(key)
            def __setattr__(self, key, value):
                self[key] = value

        self.mock_session_state = SessionStateMock()
        self.st_patcher = patch("streamlit.session_state", self.mock_session_state)
        self.st_patcher.start()

    def tearDown(self):
        self.st_patcher.stop()

    def test_1_invalid_supabase_login_fails_and_default_users_not_checked(self):
        """Test 1: Invalid Supabase credentials -> DEFAULT_USERS is NOT checked, login fails."""
        mock_client = MagicMock()
        mock_client.auth.sign_in_with_password.side_effect = Exception("Invalid login credentials")
        with patch("src.database.get_supabase_client", return_value=mock_client):
            user = verify_credentials("reviewer@preauth.med", "password123")
            self.assertIsNone(user)
            self.assertIn("Invalid credentials", self.mock_session_state.get("last_auth_error", ""))

    def test_2_valid_supabase_auth_login(self):
        """Test 2: Valid Supabase Auth login -> succeeds normally and loads profile via auth_id."""
        mock_user = MagicMock()
        mock_user.id = "auth-uuid-12345"
        mock_user.email = "cmo@preauth.med"
        mock_user.user_metadata = {"full_name": "Dr. Sarah Jenkins, MD"}

        mock_response = MagicMock()
        mock_response.user = mock_user
        mock_response.session = MagicMock()

        mock_client = MagicMock()
        mock_client.auth.sign_in_with_password.return_value = mock_response

        with patch("src.database.get_supabase_client", return_value=mock_client):
            user = verify_credentials("cmo@preauth.med", "RealPassword123!")
            self.assertIsNotNone(user)
            self.assertEqual(user["email"], "cmo@preauth.med")

    def test_3_invalid_password(self):
        """Test 3: Invalid password -> rejected (returns None and sets last_auth_error)."""
        user = verify_credentials("reviewer@preauth.med", "wrongpassword")
        self.assertIsNone(user)
        self.assertIn("Invalid credentials", self.mock_session_state.get("last_auth_error", ""))

    def test_4_invalid_username_or_email(self):
        """Test 4: Invalid username/email -> rejected (returns None and sets last_auth_error)."""
        user = verify_credentials("nonexistent_user", "password123")
        self.assertIsNone(user)
        self.assertIn("Invalid credentials", self.mock_session_state.get("last_auth_error", ""))

    def test_5_empty_credentials(self):
        """Test 5: Empty credentials -> rejected (returns None)."""
        self.assertIsNone(verify_credentials("", ""))
        self.assertIsNone(verify_credentials("reviewer", ""))
        self.assertIsNone(verify_credentials("", "password123"))

    def test_6_new_user_signup_and_login_flow(self):
        """Test 6: Register new user -> logout -> login again using Supabase Auth."""
        import uuid
        uid_str = uuid.uuid4().hex[:8]
        test_email = f"new.doctor.{uid_str}@preauth.med"
        test_pass = "SecurePass123!"
        test_name = f"Dr. New Doctor {uid_str}, MD"
        test_role = "Attending Physician / Reviewer"

        # Mock Supabase Auth for signup and login
        mock_user = MagicMock()
        mock_user.id = f"auth-uid-{uid_str}"
        mock_user.email = test_email
        mock_user.user_metadata = {"full_name": test_name, "clinical_role": test_role}

        mock_auth_resp = MagicMock()
        mock_auth_resp.user = mock_user
        mock_auth_resp.session = MagicMock()

        mock_client = MagicMock()
        mock_client.auth.sign_up.return_value = mock_auth_resp
        mock_client.auth.sign_in_with_password.return_value = mock_auth_resp

        with patch("src.database.get_supabase_client", return_value=mock_client):
            # Step A: Register new user
            registered = register_new_user(test_name, test_email, test_pass, test_role)
            self.assertIsNotNone(registered)
            self.assertEqual(registered["email"], test_email)

            # Step B: Login session
            with patch("streamlit.rerun"):
                login_user(registered)
                self.assertTrue(self.mock_session_state.get("authenticated"))
                self.assertEqual(self.mock_session_state.get("user")["email"], test_email)

            # Step C: Logout
            with patch("streamlit.rerun"):
                logout()
                self.assertFalse(self.mock_session_state.get("authenticated"))
                self.assertIsNone(self.mock_session_state.get("user"))

            # Step D: Login again using email
            relogin = verify_credentials(test_email, test_pass)
            self.assertIsNotNone(relogin)
            self.assertEqual(relogin["email"], test_email)

            # Step E: Login again using username
            username = test_email.split("@")[0]
            relogin_uname = verify_credentials(username, test_pass)
            self.assertIsNotNone(relogin_uname)
            self.assertEqual(relogin_uname["email"], test_email)

    def test_7_get_or_link_user_profile_linking(self):
        """Test 7: get_or_link_user_profile links existing profile with NULL auth_id."""
        auth_uid = "550e8400-e29b-41d4-a716-446655440000"
        email = "unlinked.user@preauth.med"

        # Create unlinked profile (auth_id = None)
        unlinked_prof = {
            "email": email,
            "username": "unlinked.user",
            "name": "Dr. Unlinked User",
            "role": "Chief Medical Officer",
            "auth_id": None
        }

        with patch("src.database.get_user_profile_by_auth_id", return_value=None), \
             patch("src.database.get_user_profile_by_email", return_value=unlinked_prof), \
             patch("src.database.save_user_profile") as mock_save:

            resolved = get_or_link_user_profile(auth_uid, email)
            self.assertIsNotNone(resolved)
            self.assertEqual(resolved["email"], email)

    def test_8_get_or_link_user_profile_creation(self):
        """Test 8: get_or_link_user_profile creates profile if genuinely missing."""
        auth_uid = "660e8400-e29b-41d4-a716-446655441111"
        email = "missing.user@preauth.med"

        with patch("src.database.get_user_profile_by_auth_id", return_value=None), \
             patch("src.database.get_user_profile_by_email", return_value=None), \
             patch("src.database.save_user_profile", return_value="generated-id"):

            created = get_or_link_user_profile(auth_uid, email, name="Dr. Missing User", role="Prior Auth Specialist")
            self.assertIsNotNone(created)
            self.assertEqual(created["email"], email)
            self.assertEqual(created["role"], "Prior Auth Specialist")

    def test_9_profile_failure_does_not_become_invalid_credentials(self):
        """Test 9: Supabase Auth succeeds but profile load fails -> profile error, NOT invalid credentials."""
        mock_auth_user = MagicMock()
        mock_auth_user.id = "user-123"
        mock_auth_user.email = "test@preauth.med"
        mock_auth_user.user_metadata = {}

        mock_auth_resp = MagicMock()
        mock_auth_resp.user = mock_auth_user
        mock_auth_resp.session = MagicMock()

        mock_client = MagicMock()
        mock_client.auth.sign_in_with_password.return_value = mock_auth_resp

        with patch("src.database.get_supabase_client", return_value=mock_client), \
             patch("src.database.get_or_link_user_profile", side_effect=Exception("DB connection error")):

            user = verify_credentials("test@preauth.med", "password123")
            self.assertIsNone(user)
            err_msg = self.mock_session_state.get("last_auth_error", "")
            self.assertIn("clinical profile could not be loaded", err_msg)
            self.assertNotIn("Invalid credentials", err_msg)

    def test_10_logout_clears_session_completely(self):
        """Test 10: Logout clears authenticated state, user profile, and error state."""
        self.mock_session_state["authenticated"] = True
        self.mock_session_state["user"] = DEFAULT_USERS["cmo@preauth.med"]
        self.mock_session_state["active_case"] = {"test": "data"}
        self.mock_session_state["nav_page"] = "policies"
        self.mock_session_state["last_auth_error"] = "Previous error"

        with patch("streamlit.rerun") as mock_rerun:
            logout()
            self.assertFalse(self.mock_session_state.get("authenticated"))
            self.assertIsNone(self.mock_session_state.get("user"))
            self.assertIsNone(self.mock_session_state.get("active_case"))
            self.assertIsNone(self.mock_session_state.get("last_auth_error"))
            self.assertEqual(self.mock_session_state.get("nav_page"), "dashboard")
            mock_rerun.assert_called_once()

    def test_11_signup_uses_email_redirect_to_env_var(self):
        """Test 11: register_new_user passes SUPABASE_REDIRECT_URL in email_redirect_to."""
        mock_auth_user = MagicMock()
        mock_auth_user.id = "redirect-test-uid"
        mock_auth_user.email = "redirect@preauth.med"
        
        mock_auth_resp = MagicMock()
        mock_auth_resp.user = mock_auth_user
        mock_auth_resp.session = None

        mock_client = MagicMock()
        mock_client.auth.sign_up.return_value = mock_auth_resp

        with patch("src.database.get_supabase_client", return_value=mock_client), \
             patch("src.database.get_or_link_user_profile") as mock_link:
            mock_link.return_value = {"email": "redirect@preauth.med", "name": "Dr. Redirect"}
            
            with patch.dict(os.environ, {"SUPABASE_REDIRECT_URL": "http://localhost:8501"}):
                res = register_new_user("Dr. Redirect", "redirect@preauth.med", "Pass123!", "Senior Clinical Reviewer")
                
            mock_client.auth.sign_up.assert_called_once()
            call_args = mock_client.auth.sign_up.call_args[0][0]
            self.assertEqual(call_args["options"]["email_redirect_to"], "http://localhost:8501")


if __name__ == "__main__":
    unittest.main()

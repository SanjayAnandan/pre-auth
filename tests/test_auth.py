"""
tests/test_auth.py - Unit tests for the authentication and session management module.
"""

import unittest
import streamlit as st
from src.auth import (
    DEFAULT_USERS,
    init_auth_session,
    verify_credentials,
    register_new_user,
)


class TestAuthModule(unittest.TestCase):
    def setUp(self):
        st.session_state.clear()
        init_auth_session()

    def test_default_users_exist(self):
        """Verify that clinical default user roles are correctly configured."""
        self.assertIn("reviewer@preauth.med", DEFAULT_USERS)
        self.assertIn("cmo@preauth.med", DEFAULT_USERS)
        self.assertIn("specialist@preauth.med", DEFAULT_USERS)
        self.assertIn("auditor@preauth.med", DEFAULT_USERS)

    def test_verify_credentials_valid(self):
        """Verify credential authentication with email and username."""
        user = verify_credentials("reviewer@preauth.med", "password123")
        self.assertIsNotNone(user)
        self.assertEqual(user["role"], "Senior Clinical Reviewer")

        user_cmo = verify_credentials("cmo", "password123")
        self.assertIsNotNone(user_cmo)
        self.assertEqual(user_cmo["role"], "Chief Medical Officer")

    def test_verify_credentials_invalid(self):
        """Verify failure cases with wrong email or password."""
        self.assertIsNone(verify_credentials("reviewer@preauth.med", "wrongpass"))
        self.assertIsNone(verify_credentials("nonexistent@med.com", "password123"))
        self.assertIsNone(verify_credentials("", ""))

    def test_init_auth_session(self):
        """Verify session state initialization."""
        self.assertFalse(st.session_state.authenticated)
        self.assertIsNone(st.session_state.user)
        self.assertEqual(st.session_state.custom_users, {})

    def test_register_new_user(self):
        """Verify registration of a new user account."""
        new_u = register_new_user(
            name="Dr. Jane Smith, MD",
            email="jane.smith@hospital.org",
            password="securepass123",
            role="Attending Physician / Reviewer"
        )
        self.assertEqual(new_u["name"], "Dr. Jane Smith, MD")
        self.assertEqual(new_u["initials"], "JS")
        self.assertEqual(new_u["badge"], "Physician Reviewer")

        # Verify authentication with newly registered credentials
        authed = verify_credentials("jane.smith@hospital.org", "securepass123")
        self.assertIsNotNone(authed)
        self.assertEqual(authed["name"], "Dr. Jane Smith, MD")


if __name__ == "__main__":
    unittest.main()

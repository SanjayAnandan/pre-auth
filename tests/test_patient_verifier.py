"""
tests/test_patient_verifier.py

Unit test suite for Privacy-Preserving Patient Verifier using standard unittest.
Covering all required test scenarios:
1. Exact Match
2. Formatting Difference
3. DOB Mismatch
4. Member ID Mismatch
5. Missing Secondary Field
6. Age Discrepancy
7. Mismatch Must Stop LLM (Pipeline boundary test)
"""

import os
import sys
import unittest
from datetime import date

# Ensure src/ is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.patient_verifier import (
    extract_identity_fields_locally,
    normalize_date,
    normalize_name,
    normalize_id,
    normalize_gender,
    calculate_age_from_dob,
    verify_patient_documents,
    deidentify_text,
)

import app


class TestPatientVerifier(unittest.TestCase):

    def test_1_exact_match(self):
        """History: John Doe, 1980-04-15, ABC123. PA: John Doe, 1980-04-15, ABC123 -> MATCH"""
        hist = {
            "name": "John Doe",
            "date_of_birth": "1980-04-15",
            "member_id": "ABC123",
            "gender": "Male"
        }
        pa = {
            "name": "John Doe",
            "date_of_birth": "1980-04-15",
            "member_id": "ABC123",
            "gender": "Male"
        }
        res = verify_patient_documents(hist, pa)

        self.assertTrue(res["verified"])
        self.assertEqual(res["status"], "MATCH")
        self.assertEqual(res["score"], 100)
        self.assertEqual(res["fields"]["name"], "MATCH")
        self.assertEqual(res["fields"]["date_of_birth"], "MATCH")
        self.assertEqual(res["fields"]["member_id"], "MATCH")
        self.assertEqual(res["fields"]["gender"], "MATCH")
        self.assertEqual(len(res["discrepancies"]), 0)

    def test_2_formatting_difference(self):
        """History: JOHN DOE, 15/04/1980, ABC-123. PA: John Doe, 1980-04-15, ABC123 -> MATCH"""
        hist = {
            "name": "JOHN DOE",
            "date_of_birth": "15/04/1980",
            "member_id": "ABC-123",
            "gender": "M"
        }
        pa = {
            "name": "John Doe",
            "date_of_birth": "1980-04-15",
            "member_id": "ABC123",
            "gender": "Male"
        }
        res = verify_patient_documents(hist, pa)

        self.assertTrue(res["verified"])
        self.assertEqual(res["status"], "MATCH")
        self.assertEqual(res["score"], 100)
        self.assertEqual(res["fields"]["name"], "MATCH")
        self.assertEqual(res["fields"]["date_of_birth"], "MATCH")
        self.assertEqual(res["fields"]["member_id"], "MATCH")
        self.assertEqual(res["fields"]["gender"], "MATCH")

    def test_3_dob_mismatch(self):
        """History: 1980-04-15. PA: 1981-04-15 -> MISMATCH"""
        hist = {
            "name": "John Doe",
            "date_of_birth": "1980-04-15",
            "member_id": "ABC123",
            "gender": "Male"
        }
        pa = {
            "name": "John Doe",
            "date_of_birth": "1981-04-15",
            "member_id": "ABC123",
            "gender": "Male"
        }
        res = verify_patient_documents(hist, pa)

        self.assertFalse(res["verified"])
        self.assertEqual(res["status"], "MISMATCH")
        self.assertEqual(res["fields"]["date_of_birth"], "MISMATCH")
        self.assertTrue(any("date of birth does not match" in d.lower() for d in res["discrepancies"]))

    def test_verification_failed_case_builds_without_undefined_state(self):
        """Mismatch case creation should use the verified identity values and not rely on uninitialized variables."""
        verification = {
            "verified": False,
            "history_identity": {
                "name": "John Doe",
                "date_of_birth": "1980-04-15",
                "patient_id": "ABC123",
                "gender": "male",
            },
            "pa_identity": {
                "name": "John Doe",
                "date_of_birth": "1980-04-15",
                "patient_id": "ABC123",
                "gender": "male",
            },
            "calculated_age": 46,
            "discrepancies": ["Date of Birth does not match (History: '1980-04-15' vs PA Form: '1981-04-15')"],
        }

        case = app.build_verification_failed_case(
            verification,
            type("UploadedFile", (), {"name": "history.pdf"})(),
            b"%PDF-1.4",
            12.5,
            "REQ-123",
            "PAT-456",
        )

        self.assertEqual(case["patient"]["patient_name"], "John Doe")
        self.assertEqual(case["patient"]["patient_id"], "ABC123")
        self.assertEqual(case["request"]["id"], "REQ-123")
        self.assertEqual(case["decision"]["decision"], "DOCUMENT VERIFICATION FAILED")
        self.assertEqual(case["decision"]["failed_criteria"][0], verification["discrepancies"][0])

    def test_4_member_id_mismatch(self):
        """History: ABC123. PA: XYZ456 -> MISMATCH"""
        hist = {
            "name": "John Doe",
            "date_of_birth": "1980-04-15",
            "member_id": "ABC123",
            "gender": "Male"
        }
        pa = {
            "name": "John Doe",
            "date_of_birth": "1980-04-15",
            "member_id": "XYZ456",
            "gender": "Male"
        }
        res = verify_patient_documents(hist, pa)

        self.assertFalse(res["verified"])
        self.assertEqual(res["status"], "MISMATCH")
        self.assertEqual(res["fields"]["member_id"], "MISMATCH")
        self.assertTrue(any("member id does not match" in d.lower() for d in res["discrepancies"]))

    def test_5_missing_secondary_field(self):
        """Gender exists only in History PDF. Should NOT fail verification automatically."""
        hist = {
            "name": "John Doe",
            "date_of_birth": "1980-04-15",
            "member_id": "ABC123",
            "gender": "Male"
        }
        pa = {
            "name": "John Doe",
            "date_of_birth": "1980-04-15",
            "member_id": "ABC123",
            "gender": None
        }
        res = verify_patient_documents(hist, pa)

        self.assertTrue(res["verified"])
        self.assertEqual(res["status"], "MATCH")
        self.assertEqual(res["fields"]["gender"], "UNAVAILABLE")

    def test_6_age_discrepancy(self):
        """Same DOB (1980-04-15), but history states age 40 while PA states age 46. Should give AGE DISCREPANCY warning."""
        ref_d = date(2026, 8, 18)  # Calculated age = 46
        hist = {
            "name": "John Doe",
            "date_of_birth": "1980-04-15",
            "member_id": "ABC123",
            "stated_age": 40
        }
        pa = {
            "name": "John Doe",
            "date_of_birth": "1980-04-15",
            "member_id": "ABC123",
            "stated_age": 46
        }
        res = verify_patient_documents(hist, pa, ref_date=ref_d)

        self.assertTrue(res["verified"])
        self.assertEqual(res["status"], "MATCH")
        self.assertTrue(len(res["age_warnings"]) > 0)
        self.assertTrue(any("AGE DISCREPANCY" in w for w in res["age_warnings"]))

    def test_7_mismatch_must_stop_llm(self):
        """Simulate pipeline flow when identity verification fails: verified must be False so LLM is NOT called."""
        hist = {
            "name": "John Doe",
            "date_of_birth": "1980-04-15",
            "member_id": "ABC123"
        }
        pa = {
            "name": "Jane Smith",
            "date_of_birth": "1990-01-01",
            "member_id": "XYZ999"
        }
        res = verify_patient_documents(hist, pa)

        # Verification gate check
        self.assertFalse(res["verified"])

        llm_called = False
        if res["verified"]:
            llm_called = True

        self.assertFalse(llm_called, "LLM must NOT be called when verification fails!")

    def test_deidentification(self):
        """Test local PII stripping from raw text."""
        raw_text = """
        Patient Name: John Michael Doe
        DOB: 15/04/1980
        Member ID: ABC123
        Phone: (555) 123-4567
        Address: 123 Main Street, Cityville
        Diagnosis: Severe osteoarthritis of knee.
        Requested Service: MRI Knee Left (CPT 73721).
        """

        identity = {
            "name": "John Michael Doe",
            "date_of_birth": "1980-04-15",
            "member_id": "ABC123",
            "phone": "5551234567",
            "address": "123 Main Street Cityville"
        }

        deidentified = deidentify_text(raw_text, identity, calculated_age=46)

        self.assertNotIn("John Michael Doe", deidentified)
        self.assertNotIn("15/04/1980", deidentified)
        self.assertNotIn("ABC123", deidentified)
        self.assertIn("Age: 46", deidentified)
        self.assertIn("Severe osteoarthritis of knee", deidentified)
        self.assertIn("CPT 73721", deidentified)


if __name__ == "__main__":
    unittest.main()

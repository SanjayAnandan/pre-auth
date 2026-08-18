"""
tests/test_pdf_report.py - Test suite for PDF Report Generation Module
"""

import unittest
from src.pdf_report import generate_report, clean_txt, format_display_date


class TestPDFReportGenerator(unittest.TestCase):

    def test_clean_txt_and_formatting(self):
        self.assertEqual(clean_txt(None), "N/A")
        self.assertEqual(clean_txt(""), "N/A")
        self.assertEqual(clean_txt("  John & Smith <MD>  "), "John &amp; Smith &lt;MD&gt;")
        self.assertEqual(format_display_date("1980-04-15"), "15-Apr-1980")
        self.assertEqual(format_display_date(None), "N/A")

    def test_approved_report_generation(self):
        case_data = {
            "patient": {
                "patient_name": "John Michael Doe",
                "patient_id": "PT-10294",
                "date_of_birth": "1980-04-15",
                "age": 46,
                "gender": "Male",
                "member_id": "ABC123456",
                "payer": "Aetna",
                "plan_type": "PPO",
                "phone": "555-0192",
                "email": "jdoe@example.com",
                "address": "123 Main St, Anytown, USA"
            },
            "verification": {
                "verified": True,
                "status": "MATCH",
                "fields": {
                    "name": "MATCH",
                    "patient_id": "MATCH",
                    "member_id": "MATCH",
                    "date_of_birth": "MATCH",
                    "gender": "MATCH"
                }
            },
            "request": {
                "id": "PA-2026-00124",
                "requested_service": "MRI Brain",
                "cpt_hcpcs_code": "70551",
                "payer": "Aetna",
                "status": "APPROVED"
            },
            "decision": {
                "policy_name": "MRI Brain Imaging Policy",
                "policy_id": "MRI-001",
                "policy_version": "v2.1",
                "decision": "APPROVED",
                "reason": "All required authorization criteria were satisfied."
            },
            "criteria": [
                {"criterion": "Clinical Indication", "status": "PASSED", "reason": "Severe headache present for > 4 weeks"},
                {"criterion": "Age Requirement", "status": "PASSED", "reason": "Patient is > 18 years old"},
                {"criterion": "Prior Conservative Therapy", "status": "PASSED", "reason": "Documented medication trial for 6 weeks"}
            ]
        }

        pdf_bytes = generate_report(case_data)
        self.assertIsInstance(pdf_bytes, bytes)
        self.assertGreater(len(pdf_bytes), 1000)
        self.assertTrue(pdf_bytes.startswith(b"%PDF-"))

    def test_denied_report_generation(self):
        case_data = {
            "patient": {
                "patient_name": "Jane Smith",
                "patient_id": "PT-90123",
                "payer": "BlueCross"
            },
            "request": {
                "id": "REQ-DENIED-001",
                "requested_service": "Total Knee Arthroplasty",
                "cpt_hcpcs_code": "27447"
            },
            "decision": {
                "decision": "DENIED",
                "policy_name": "Knee Surgery Policy",
                "policy_id": "SURG-002",
                "reason": "Conservative physical therapy requirement not met.",
                "failed_criteria": ["Minimum 6 weeks physical therapy documented"]
            },
            "criteria": [
                {"criterion": "Conservative Therapy", "status": "FAILED", "reason": "Only 2 weeks documented"},
                {"criterion": "X-Ray Evidence", "status": "PASSED", "reason": "Severe joint space narrowing"}
            ]
        }

        pdf_bytes = generate_report(case_data)
        self.assertIsInstance(pdf_bytes, bytes)
        self.assertGreater(len(pdf_bytes), 1000)
        self.assertTrue(pdf_bytes.startswith(b"%PDF-"))

    def test_mismatch_report_generation(self):
        case_data = {
            "patient": {
                "patient_name": "John Michael Doe",
                "patient_id": "PT-10294"
            },
            "verification": {
                "verified": False,
                "status": "MISMATCH",
                "fields": {
                    "name": "MATCH",
                    "patient_id": "MISMATCH",
                    "member_id": "MISMATCH",
                    "date_of_birth": "MATCH",
                    "gender": "MATCH"
                },
                "history_identity": {"patient_id": "PT-10294", "member_id": "ABC123456"},
                "pa_identity": {"patient_id": "PT-20481", "member_id": "XYZ789012"}
            },
            "request": {
                "id": "REQ-MISMATCH-99",
                "requested_service": "MRI Brain",
                "cpt_hcpcs_code": "70551",
                "status": "DOCUMENT VERIFICATION FAILED"
            },
            "decision": {
                "decision": "DOCUMENT VERIFICATION FAILED",
                "reason": "Identity verification between submitted Patient History and PA Request Form failed."
            }
        }

        pdf_bytes = generate_report(case_data)
        self.assertIsInstance(pdf_bytes, bytes)
        self.assertGreater(len(pdf_bytes), 1000)
        self.assertTrue(pdf_bytes.startswith(b"%PDF-"))

    def test_no_prior_auth_report_generation(self):
        case_data = {
            "patient": {
                "patient_name": "Robert Brown",
                "patient_id": "PT-5541"
            },
            "request": {
                "id": "REQ-NOPA-10",
                "requested_service": "Routine Diagnostic X-Ray",
                "cpt_hcpcs_code": "71045",
                "status": "NO PRIOR AUTH REQUIRED"
            },
            "decision": {
                "decision": "NO PRIOR AUTH REQUIRED",
                "reason": "Chest X-Ray is exempt from prior authorization."
            }
        }

        pdf_bytes = generate_report(case_data)
        self.assertIsInstance(pdf_bytes, bytes)
        self.assertGreater(len(pdf_bytes), 1000)
        self.assertTrue(pdf_bytes.startswith(b"%PDF-"))


if __name__ == "__main__":
    unittest.main()

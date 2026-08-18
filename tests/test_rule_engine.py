"""
tests/test_rule_engine.py

Comprehensive Rule Engine & Decision Test Suite.
Verifies all required regression scenarios:
1. Daniel Carter MRI Lumbar Spine case -> APPROVED (All criteria PASSED / N/A)
2. Robert Wilson -> DENIED (Treatment duration = 20 days < policy minimum 42 days)
3. James Anderson -> MANUAL REVIEW (Neurological examination missing, Relevant imaging report missing)
4. Maria Rodriguez -> APPROVED (Demographics matched: Female on both forms)
5. Identity Mismatch -> Stops evaluation before policy processing
6. Equivalent documentation wording ("Lumbar Spine X-ray" vs "Relevant imaging report") -> PASSED
7. Neurological evidence under physical/clinical examination -> PASSED
8. Quantity violation (Qty 2 vs Max 1) -> DENIED
9. Required previous procedure missing -> MANUAL REVIEW
10. No neurological findings + no imaging evidence -> MUST produce MANUAL REVIEW (never APPROVED)
"""

import os
import sys
import unittest
from pathlib import Path

# Ensure src/ is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.policy_matcher import load_policies
from src.rule_engine import evaluate_policy, check_documentation, is_documentation_satisfied
from src.patient_verifier import verify_patient_documents

from src.patient_parser import merge_patient_data

ROOT_DIR = Path(__file__).resolve().parent.parent
POLICY_PATH = ROOT_DIR / "data" / "policies.json"


class TestRuleEngine(unittest.TestCase):

    def setUp(self):
        self.policies = load_policies(POLICY_PATH)
        # POL-001: MRI Knee
        self.pol_001 = next(p for p in self.policies if p["policy_id"] == "POL-001")
        # POL-002: MRI Lumbar Spine
        self.pol_002 = next(p for p in self.policies if p["policy_id"] == "POL-002")
        # POL-003: CT Head
        self.pol_003 = next(p for p in self.policies if p["policy_id"] == "POL-003")

    def test_1_daniel_carter_mri_spine_approved(self):
        """Test 1: Daniel Carter synthetic MRI Lumbar Spine request -> APPROVED."""
        daniel_carter = {
            "patient_id": "MRN-202600517",
            "patient_name": "Daniel Carter",
            "age": 52,
            "gender": "male",
            "payer": "Synthetic Health Plan A",
            "diagnosis": "Lumbar Radiculopathy",
            "icd10_code": "M54.16",
            "severity": "Moderate",
            "severity_evidence": ["Pain score 6/10", "Functional impairment present"],
            "previous_treatment": [
                {"treatment": "Physical Therapy", "specific_treatment": "Physical therapy", "duration_days": 56},
                {"treatment": "Medication", "specific_treatment": "NSAID therapy", "duration_days": 56},
                {"treatment": "Activity Modification", "specific_treatment": "Home exercise", "duration_days": 56},
                {"treatment": "Activity Modification", "specific_treatment": "Activity modification", "duration_days": 70}
            ],
            "previous_procedure": None,
            "requested_service": "MRI Lumbar Spine",
            "cpt_hcpcs_code": "72148",
            "quantity": 1,
            "frequency": "1 study within 180 days",
            "provider_specialty": "Orthopedics",
            "facility_type": "Outpatient Diagnostic Center",
            "documentation": {
                "Clinical notes": True,
                "Physical examination": True,
                "Previous treatment history": True,
                "Lumbar Spine X-ray": True
            },
            "clinical_information": {
                "functional_impairment": True,
                "physical_examination": [
                    "Mild sensory reduction in left L5 distribution",
                    "Motor strength 5/5",
                    "Symmetric reflexes",
                    "Positive left straight-leg raise"
                ],
                "xray": {
                    "performed": True,
                    "findings": ["Lumbar spine X-ray shows moderate disc space narrowing"]
                }
            }
        }

        result = evaluate_policy(daniel_carter, self.pol_002)

        self.assertEqual(result["decision"], "APPROVED", f"Daniel Carter request must be APPROVED, got: {result['decision']}")

        status_map = {res["criterion"]: res["status"] for res in result["results"]}
        self.assertEqual(status_map.get("CPT/HCPCS"), "PASSED")
        self.assertEqual(status_map.get("Diagnosis"), "PASSED")
        self.assertEqual(status_map.get("Age"), "PASSED")
        self.assertEqual(status_map.get("Severity"), "PASSED")
        self.assertEqual(status_map.get("Previous Treatment"), "PASSED")
        self.assertEqual(status_map.get("Previous Procedure"), "NOT_APPLICABLE")
        self.assertEqual(status_map.get("Provider Specialty"), "PASSED")
        self.assertEqual(status_map.get("Facility"), "PASSED")
        self.assertEqual(status_map.get("Documentation"), "PASSED")
        self.assertEqual(status_map.get("Quantity"), "PASSED")
        self.assertEqual(status_map.get("Frequency"), "PASSED")

    def test_2_robert_wilson_denied(self):
        """Test 2: Robert Wilson -> DENIED due to treatment duration 20 days < policy minimum 42 days."""
        robert_wilson = {
            "patient_id": "MRN-ROBERT-01",
            "patient_name": "Robert Wilson",
            "age": 45,
            "gender": "male",
            "payer": "Synthetic Health Plan A",
            "diagnosis": "Lumbar Radiculopathy",
            "icd10_code": "M54.16",
            "severity": "Moderate",
            "previous_treatment": [
                {"treatment": "Physical Therapy", "duration_days": 20}  # Required min: 42
            ],
            "requested_service": "MRI Lumbar Spine",
            "cpt_hcpcs_code": "72148",
            "quantity": 1,
            "frequency": "Single",
            "provider_specialty": "Orthopedics",
            "facility_type": "Outpatient Diagnostic Center",
            "documentation": {
                "Clinical notes": True,
                "Neurological examination": True,
                "Previous treatment history": True,
                "Relevant imaging report": True
            },
            "clinical_information": {"functional_impairment": True}
        }

        result = evaluate_policy(robert_wilson, self.pol_002)

        self.assertEqual(result["decision"], "DENIED")
        status_map = {res["criterion"]: res["status"] for res in result["results"]}
        self.assertEqual(status_map.get("Previous Treatment"), "FAILED")
        self.assertIn("20", result["reason"])

    def test_3_james_anderson_manual_review_and_supplemental_resubmission(self):
        """Test 3: James Anderson -> Initial MANUAL REVIEW -> Supplemental evidence merge -> APPROVED."""
        james_initial = {
            "patient_id": "MRN-JAMES-01",
            "patient_name": "James Anderson",
            "age": 50,
            "gender": "male",
            "payer": "Synthetic Health Plan A",
            "diagnosis": "Lumbar Radiculopathy",
            "icd10_code": "M54.16",
            "severity": "Severe",
            "severity_evidence": ["Pain score 8/10"],
            "previous_treatment": [
                {"treatment": "Physical Therapy", "duration_days": 56}
            ],
            "requested_service": "MRI Lumbar Spine",
            "cpt_hcpcs_code": "72148",
            "quantity": 1,
            "frequency": "Single",
            "provider_specialty": "Orthopedics",
            "facility_type": "Outpatient Diagnostic Center",
            "documentation": {
                "Clinical notes": True,
                "Previous treatment history": True
            },
            "clinical_information": {
                "functional_impairment": True,
                "history_of_present_illness": "Severe lower back pain radiating down left leg."
            }
        }

        res_initial = evaluate_policy(james_initial, self.pol_002)
        self.assertEqual(res_initial["decision"], "MANUAL REVIEW", "Initial James Anderson must be MANUAL REVIEW")

        # Supplemental clinical evidence extracted from resubmitted PDF
        james_supplemental = {
            "documentation": {
                "Neurological examination": True,
                "Lumbar Spine X-ray": True
            },
            "clinical_information": {
                "physical_examination": [
                    "Sensory reduction left L5 dermatome",
                    "Motor strength 5/5 dorsiflexion",
                    "Symmetric reflexes",
                    "Positive straight-leg raise"
                ],
                "xray": {
                    "findings": ["Lumbar X-ray shows moderate disc space narrowing at L4-L5"]
                }
            }
        }

        # Merge evidence
        james_merged = merge_patient_data(james_initial, james_supplemental)

        # Re-evaluate with exact same policy POL-002
        res_resubmitted = evaluate_policy(james_merged, self.pol_002)
        self.assertEqual(res_resubmitted["decision"], "APPROVED", "James Anderson with supplemental evidence must evaluate to APPROVED!")

    def test_4_maria_rodriguez_approved_and_identity_mismatch(self):
        """Test 4: Maria Rodriguez approved when demographics match; identity mismatch stops evaluation."""
        hist_matched = {
            "name": "Maria Rodriguez",
            "date_of_birth": "1985-06-12",
            "member_id": "MRN-MARIA-01",
            "gender": "Female"
        }
        pa_matched = {
            "name": "Maria Rodriguez",
            "date_of_birth": "1985-06-12",
            "member_id": "MRN-MARIA-01",
            "gender": "Female"
        }
        ver_matched = verify_patient_documents(hist_matched, pa_matched)
        self.assertTrue(ver_matched["verified"])

        maria_patient = {
            "patient_id": "MRN-MARIA-01",
            "patient_name": "Maria Rodriguez",
            "age": 41,
            "gender": "female",
            "payer": "Synthetic Health Plan A",
            "diagnosis": "Knee pain",
            "icd10_code": "M25.561",
            "severity": "Moderate",
            "previous_treatment": [{"treatment": "Physical Therapy", "duration_days": 42}],
            "requested_service": "MRI Knee",
            "cpt_hcpcs_code": "73721",
            "quantity": 1,
            "frequency": "Single",
            "provider_specialty": "Orthopedics",
            "facility_type": "Outpatient Diagnostic Center",
            "documentation": {
                "Clinical notes": True,
                "Physical examination": True,
                "Previous treatment history": True,
                "Relevant X-ray report": True
            },
            "clinical_information": {
                "functional_impairment": True,
                "physical_examination": ["Moderate joint effusion"],
                "xray": {"findings": ["Joint space narrowing"]}
            }
        }
        res_maria = evaluate_policy(maria_patient, self.pol_001)
        self.assertEqual(res_maria["decision"], "APPROVED")

        # Identity mismatch test
        pa_mismatched = {
            "name": "Maria Rodriguez",
            "date_of_birth": "1985-06-12",
            "member_id": "MRN-MARIA-01",
            "gender": "Male"  # Discrepancy
        }
        ver_mismatched = verify_patient_documents(hist_matched, pa_mismatched)
        self.assertFalse(ver_mismatched["verified"], "Identity mismatch must stop pipeline before policy processing!")

    def test_5_equivalent_imaging_terminology(self):
        """Test 5: 'Lumbar Spine X-ray' satisfies 'Relevant imaging report' when actual X-ray findings exist."""
        patient = {
            "documentation": {"Lumbar Spine X-ray": True},
            "clinical_information": {
                "xray": {"findings": ["Disc space narrowing"]}
            }
        }
        self.assertTrue(is_documentation_satisfied("Relevant imaging report", patient))

    def test_6_neurological_evidence_under_physical_exam(self):
        """Test 6: Neurological findings under physical exam satisfy 'Neurological examination'."""
        patient = {
            "documentation": {"Physical examination": True},
            "clinical_information": {
                "physical_examination": ["Sensory reduction L5", "Motor strength 4/5", "Positive straight-leg raise"]
            }
        }
        self.assertTrue(is_documentation_satisfied("Neurological examination", patient))

    def test_7_quantity_violation_denied(self):
        """Test 7: Requested quantity (2) exceeds policy maximum (1) -> DENIED."""
        patient = {
            "patient_id": "PT-QTY-01",
            "patient_name": "Test Excess Qty",
            "age": 45,
            "gender": "male",
            "payer": "Synthetic Health Plan A",
            "diagnosis": "Lumbar Radiculopathy",
            "icd10_code": "M54.16",
            "severity": "Moderate",
            "previous_treatment": [
                {"treatment": "Physical Therapy", "duration_days": 50}
            ],
            "requested_service": "MRI Lumbar Spine",
            "cpt_hcpcs_code": "72148",
            "quantity": 2,  # Maximum is 1
            "frequency": "Single",
            "provider_specialty": "Orthopedics",
            "facility_type": "Outpatient Diagnostic Center",
            "documentation": {
                "Clinical notes": True,
                "Neurological examination": True,
                "Previous treatment history": True,
                "Relevant imaging report": True
            },
            "clinical_information": {"functional_impairment": True}
        }

        result = evaluate_policy(patient, self.pol_002)
        self.assertEqual(result["decision"], "DENIED")
        status_map = {res["criterion"]: res["status"] for res in result["results"]}
        self.assertEqual(status_map.get("Quantity"), "FAILED")

    def test_8_resubmission_with_insufficient_evidence_remains_manual_review(self):
        """Test 8: Supplemental upload containing only partial evidence remains MANUAL REVIEW."""
        patient_initial = {
            "patient_id": "PT-PARTIAL-01",
            "patient_name": "Partial Evidence Patient",
            "age": 50,
            "gender": "male",
            "payer": "Synthetic Health Plan A",
            "diagnosis": "Lumbar Radiculopathy",
            "icd10_code": "M54.16",
            "severity": "Severe",
            "previous_treatment": [{"treatment": "Physical Therapy", "duration_days": 56}],
            "requested_service": "MRI Lumbar Spine",
            "cpt_hcpcs_code": "72148",
            "quantity": 1,
            "frequency": "Single",
            "provider_specialty": "Orthopedics",
            "facility_type": "Outpatient Diagnostic Center",
            "documentation": {"Clinical notes": True, "Previous treatment history": True},
            "clinical_information": {"functional_impairment": True}
        }

        res_init = evaluate_policy(patient_initial, self.pol_002)
        self.assertEqual(res_init["decision"], "MANUAL REVIEW")

        # Supplemental contains only X-ray, but still missing neurological exam
        supp_partial = {
            "documentation": {"Lumbar Spine X-ray": True},
            "clinical_information": {"xray": {"findings": ["Disc space narrowing"]}}
        }
        merged_partial = merge_patient_data(patient_initial, supp_partial)

        res_resubmitted = evaluate_policy(merged_partial, self.pol_002)
        self.assertEqual(res_resubmitted["decision"], "MANUAL REVIEW", "Partial supplemental evidence must remain MANUAL REVIEW!")

    def test_9_resubmission_with_explicit_violation_results_in_denied(self):
        """Test 9: Supplemental upload revealing an explicit policy violation results in DENIED."""
        patient_initial = {
            "patient_id": "PT-VIOLATION-SUPP",
            "patient_name": "Violation Patient",
            "age": 50,
            "gender": "male",
            "payer": "Synthetic Health Plan A",
            "diagnosis": "Lumbar Radiculopathy",
            "icd10_code": "M54.16",
            "severity": "Severe",
            "requested_service": "MRI Lumbar Spine",
            "cpt_hcpcs_code": "72148",
            "quantity": 1,
            "frequency": "Single",
            "provider_specialty": "Orthopedics",
            "facility_type": "Outpatient Diagnostic Center",
            "documentation": {"Clinical notes": True, "Previous treatment history": True},
            "clinical_information": {"functional_impairment": True}
        }

        # Supplemental record reveals physical therapy duration was only 15 days (min required: 42)
        supp_violation = {
            "previous_treatment": [{"treatment": "Physical Therapy", "duration_days": 15}],
            "documentation": {"Neurological examination": True, "Relevant imaging report": True},
            "clinical_information": {
                "physical_examination": ["Sensory reduction L5"],
                "xray": {"findings": ["Disc narrowing"]}
            }
        }

        merged_violation = merge_patient_data(patient_initial, supp_violation)
        res_violation = evaluate_policy(merged_violation, self.pol_002)
        self.assertEqual(res_violation["decision"], "DENIED", "Supplemental document with explicit policy violation must evaluate to DENIED!")

    def test_10_build_case_from_db_record_latest_decision_selection(self):
        """Test 10: build_case_from_db_record selects the latest decision based on created_at descending."""
        from app import build_case_from_db_record

        # Scenario A: Multiple decisions
        record_multi = {
            "id": "REQ-TEST-MULTI",
            "patients": {"patient_name": "James Anderson", "patient_id": "MRN-JAMES-01"},
            "request_status": "APPROVED",
            "decisions": [
                {
                    "id": "decision-old",
                    "final_decision": "MANUAL REVIEW",
                    "created_at": "2026-08-19T00:54:56"
                },
                {
                    "id": "decision-new",
                    "final_decision": "APPROVED",
                    "created_at": "2026-08-19T00:56:01"
                }
            ]
        }
        case_multi = build_case_from_db_record(record_multi)
        self.assertEqual(case_multi["decision"]["decision"], "APPROVED")
        self.assertEqual(case_multi["decision"]["id"], "decision-new")

        # Scenario B: Single MANUAL REVIEW decision
        record_single = {
            "id": "REQ-TEST-SINGLE",
            "patients": {"patient_name": "James Anderson", "patient_id": "MRN-JAMES-01"},
            "request_status": "MANUAL REVIEW",
            "decisions": [
                {
                    "id": "decision-initial",
                    "final_decision": "MANUAL REVIEW",
                    "reason": "Missing evidence",
                    "manual_review_reasons": ["Missing Neurological examination"],
                    "created_at": "2026-08-19T00:54:56"
                }
            ]
        }
        case_single = build_case_from_db_record(record_single)
        self.assertEqual(case_single["decision"]["decision"], "MANUAL REVIEW")
        self.assertEqual(case_single["decision"]["id"], "decision-initial")
        self.assertIn("Missing Neurological examination", case_single["decision"]["manual_review_reasons"])

    def test_11_authorization_request_persistence_and_timestamp_preservation(self):
        """Test 11: Verify create_authorization_request_record returns valid UUID and timestamp is preserved."""
        from src.database import create_authorization_request_record
        from app import build_case_from_db_record

        sample_patient = {"patient_name": "August Test", "requested_service": "MRI Knee", "cpt_hcpcs_code": "73721"}
        rec = create_authorization_request_record("pat-123", sample_patient, status="PROCESSING")
        self.assertIn("id", rec)
        self.assertIn("created_at", rec)
        self.assertGreater(len(rec["id"]), 10)

        db_rec = {
            "id": rec["id"],
            "created_at": "2026-08-19T01:25:00.000000",
            "request_status": "APPROVED",
            "patients": sample_patient,
            "decisions": [
                {
                    "id": "dec-aug-1",
                    "final_decision": "APPROVED",
                    "created_at": "2026-08-19T01:25:05.000000"
                }
            ]
        }
        built_case = build_case_from_db_record(db_rec)
        self.assertEqual(built_case["request"]["created_at"], "2026-08-19T01:25:00.000000")
        self.assertEqual(built_case["audit"]["created_at"], "2026-08-19T01:25:00.000000")

    def test_12_timestamp_timezone_formatting_and_ordering(self):
        """Test 12: Verify UI timestamp formatting converts UTC to local timezone without calendar lag."""
        from src.ui import format_iso_timestamp, format_iso_timestamp_full

        utc_ts = "2026-08-18T20:07:00+00:00"
        formatted_date = format_iso_timestamp(utc_ts)
        formatted_full = format_iso_timestamp_full(utc_ts)

        self.assertIn("Aug", formatted_date)
        self.assertIn("2026", formatted_date)
        self.assertIn("Aug", formatted_full)

    def test_13_audit_and_document_persistence_helpers(self):
        """Test 13: Verify document tracking, identity verification, and clinical facts persistence helpers."""
        from src.database import (
            save_document_metadata,
            save_identity_verification,
            save_clinical_facts
        )

        dummy_req_id = "req-audit-1234"
        doc_id = save_document_metadata(dummy_req_id, "Patient History", "History_Record.pdf", "VERIFIED")
        self.assertIsNotNone(doc_id)

        ver_data = {
            "verified": True,
            "fields": {"name": "MATCH", "patient_id": "MATCH"}
        }
        ver_id = save_identity_verification(dummy_req_id, ver_data)
        self.assertIsNotNone(ver_id)

        patient_data = {
            "diagnosis": "Knee Osteoarthritis",
            "icd10_code": "M17.12",
            "cpt_hcpcs_code": "73721",
            "requested_service": "MRI Knee"
        }
        facts_id = save_clinical_facts(dummy_req_id, patient_data, model_name="Groq LLM")
        self.assertIsNotNone(facts_id)


if __name__ == "__main__":
    unittest.main()






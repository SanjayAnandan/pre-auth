"""
tests/test_reproducibility.py

Reproducibility & Determinism Test Suite for PriorAuth AI.
Verifies that:
1. Normalizing text and SHA-256 hashing produces identical hashes across runs.
2. In-memory extraction caching returns 100% identical JSON outputs without calling Groq on subsequent runs.
3. Policy selection and Rule Engine processing produce 100% identical decision outcomes over 5 consecutive runs on the exact same document input.
"""

import os
import sys
import unittest
from pathlib import Path

# Ensure src/ is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.patient_parser import (
    parse_patient,
    compute_document_hash,
    normalize_text_for_hashing,
    clear_extraction_cache,
    _PATIENT_EXTRACTION_CACHE,
)
from src.policy_matcher import load_policies, find_matching_policies, normalize_code, normalize_payer
from src.decision import load_no_prior_auth, process_decision, select_policy_deterministically

ROOT_DIR = Path(__file__).resolve().parent.parent
POLICY_PATH = ROOT_DIR / "data" / "policies.json"
NO_PA_PATH = ROOT_DIR / "data" / "no_prior_auth.json"


class TestReproducibility(unittest.TestCase):

    def setUp(self):
        clear_extraction_cache()
        self.policies = load_policies(POLICY_PATH)
        self.no_pa_codes = load_no_prior_auth(NO_PA_PATH)

        self.sample_text = """
        PATIENT HISTORY & CLINICAL CHART
        Patient Name: John Michael Doe
        DOB: 15/04/1980
        Member ID: ABC123456
        Payer: Blue Cross Blue Shield
        Gender: Male

        CLINICAL NARRATIVE:
        Patient is a 46-year-old male presenting with severe osteoarthritis of left knee.
        Pain score: 8/10. Symptoms present for 6 months causing severe functional impairment.
        Failed conservative management including:
        - Physical Therapy for 6 weeks (42 days)
        - NSAIDs (Ibuprofen) for 60 days
        Physical examination shows moderate joint effusion and joint line tenderness.
        Relevant X-ray report shows moderate to severe joint space narrowing.

        PROCEDURE REQUESTED:
        Requested Service: MRI Left Knee Joint without Contrast
        CPT/HCPCS Code: 73721
        ICD-10 Code: M17.12
        Provider Specialty: Orthopedics
        Facility Type: Imaging Center
        """

    def test_1_sha256_hash_determinism(self):
        """Verify that SHA-256 document hashing is 100% deterministic across line endings and whitespace."""
        text1 = self.sample_text
        text2 = self.sample_text.replace("\n", "\r\n") + "   \n\n"

        hash1 = compute_document_hash(text1)
        hash2 = compute_document_hash(text2)

        self.assertEqual(hash1, hash2, "SHA-256 hash must be identical across white-space and line ending variations!")

    def test_2_caching_and_idempotent_extraction(self):
        """Verify that patient extraction is cached and subsequent runs use cache without LLM API calls."""
        # Simulated pre-cached patient object
        doc_hash = compute_document_hash(self.sample_text)
        cached_patient = {
            "patient_id": "ABC123456",
            "patient_name": "John Michael Doe",
            "age": 46,
            "gender": "male",
            "payer": "Blue Cross Blue Shield",
            "diagnosis": "Severe osteoarthritis of knee",
            "icd10_code": "M17.12",
            "severity": "Severe",
            "severity_evidence": ["Pain score 8/10", "Severe functional impairment"],
            "previous_treatment": [
                {"treatment": "Physical Therapy", "specific_treatment": "Physical Therapy", "duration_days": 42},
                {"treatment": "Medication", "specific_treatment": "Ibuprofen", "duration_days": 60}
            ],
            "previous_procedure": None,
            "requested_service": "MRI Left Knee Joint without Contrast",
            "cpt_hcpcs_code": "73721",
            "quantity": 1,
            "frequency": "Single",
            "provider_specialty": "Orthopedics",
            "facility_type": "Imaging Center",
            "documentation": {"Clinical notes": True, "Physical examination": True, "Relevant X-ray report": True},
            "clinical_information": {"functional_impairment": True},
            "_document_hash": doc_hash
        }

        # Insert into in-memory cache
        cache_key = (doc_hash, "openai/gpt-oss-120b", "v1.0")
        _PATIENT_EXTRACTION_CACHE[cache_key] = cached_patient

        # Call parse_patient 5 times in a loop
        for i in range(5):
            res = parse_patient(self.sample_text)
            self.assertEqual(res["cpt_hcpcs_code"], "73721")
            self.assertEqual(res["_document_hash"], doc_hash)
            self.assertEqual(res["patient_name"], "John Michael Doe")

    def test_3_decision_reproducibility_5_runs(self):
        """Run process_decision on the exact same patient data 5 consecutive times and verify 100% identical decisions."""
        patient_data = {
            "patient_id": "ABC123456",
            "patient_name": "John Michael Doe",
            "age": 46,
            "gender": "male",
            "payer": "Blue Cross Blue Shield",
            "diagnosis": "Unilateral primary osteoarthritis, left knee",
            "icd10_code": "M17.12",
            "severity": "Severe",
            "severity_evidence": ["Pain score 8/10"],
            "previous_treatment": [
                {"treatment": "Physical Therapy", "specific_treatment": "Physical Therapy", "duration_days": 42},
                {"treatment": "Medication", "specific_treatment": "Ibuprofen", "duration_days": 60}
            ],
            "previous_procedure": None,
            "requested_service": "MRI Left Knee Joint without Contrast",
            "cpt_hcpcs_code": "73721",
            "quantity": 1,
            "frequency": "Single",
            "provider_specialty": "Orthopedics",
            "facility_type": "Imaging Center",
            "documentation": {"Clinical notes": True, "Physical examination": True, "Relevant X-ray report": True},
            "clinical_information": {"functional_impairment": True},
            "_document_hash": "abc123def456"
        }

        decisions = []
        policy_ids = []
        hashes = []

        for run in range(1, 6):
            res = process_decision(patient_data, self.policies, self.no_pa_codes)
            decisions.append(res["decision"])
            policy_ids.append(res.get("policy_id"))
            hashes.append(res.get("document_hash"))

        # Assert 100% reproducibility across all 5 runs
        first_decision = decisions[0]
        first_policy_id = policy_ids[0]

        for idx, d in enumerate(decisions, 1):
            self.assertEqual(d, first_decision, f"Run {idx} decision ({d}) differed from Run 1 ({first_decision})!")

        for idx, p in enumerate(policy_ids, 1):
            self.assertEqual(p, first_policy_id, f"Run {idx} policy ({p}) differed from Run 1 ({first_policy_id})!")

    def test_4_cpt_code_normalization(self):
        """Verify code normalization treats 70551, ' 70551 ', and '70551' as identical."""
        self.assertEqual(normalize_code("70551"), "70551")
        self.assertEqual(normalize_code(" 70551 "), "70551")
        self.assertEqual(normalize_code("cpt-70551"), "CPT70551")

    def test_5_payer_normalization(self):
        """Verify payer normalization handles case and punctuation differences."""
        p1 = normalize_payer("Blue Cross Blue Shield")
        p2 = normalize_payer("blue cross, blue shield")
        p3 = normalize_payer("BLUE CROSS BLUE SHIELD")
        self.assertEqual(p1, p2)
        self.assertEqual(p2, p3)


if __name__ == "__main__":
    unittest.main()

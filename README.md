# PREAUTH — Intelligent Healthcare Prior Authorization Management System

---

## 1. Executive Summary & Introduction

### 📌 Problem Statement
In modern healthcare systems, **Prior Authorization (PA)** is a costly administrative bottleneck. Healthcare providers must submit clinical documentation to health insurance payers before conducting specific procedures, prescribing high-cost medications, or scheduling advanced diagnostics. 

Traditional prior authorization workflows suffer from:
- **Manual Overhead:** Nurses and clinical staff spend hours manually extracting patient history, ICD-10 codes, and CPT/HCPCS procedure codes from clinical PDFs.
- **Delayed Patient Care:** Manual review turnaround times range from 2 to 14 days, leading to delayed treatments and adverse health outcomes.
- **High Error & Denial Rates:** Mismatched patient details, incomplete documentation, or failure to meet step-therapy requirements lead to unnecessary claim denials.
- **Lack of Transparency:** Neither providers nor patients have visibility into why a request failed or what specific clinical criteria were missing.

### 💡 Core Solution
**PREAUTH** is an enterprise-grade AI-powered Healthcare Prior Authorization Intake & Decision Automation Platform built with Python, Streamlit, Groq LLM (`llama-3.3-70b-versatile`), ML Risk Modeling, Deterministic Policy Engines, and Supabase PostgreSQL.

The system automates the end-to-end Prior Authorization lifecycle:
1. **Clinical PDF Ingestion & OCR:** Extracts text automatically from clinical charts, discharge summaries, and referral documents.
2. **Patient Identity Verification & PHI Privacy:** Validates demographic data (Name, DOB, Patient ID) and applies PHI masking/de-identification.
3. **Structured Entity Extraction (Groq LLM):** Maps unstructured medical text into structured JSON containing ICD-10 diagnosis, CPT codes, clinical severity, prior therapies, and lab evidence.
4. **Fast-Track Exclusions Check:** Identifies procedures that do not require prior authorization (`no_prior_auth.json`).
5. **Machine Learning Risk Prediction:** Generates statistical risk probabilities for Approval, Denial, or Manual Review based on historical patterns.
6. **Deterministic Policy Evaluation:** Evaluates strict clinical rules (Step therapy, severity criteria, documentation completeness) against payer policy guidelines (`policies.json`).
7. **Clinical SaaS UI & Database Synchronization:** Displays interactive case files, audit trails, policy management, and persists structured records to Supabase PostgreSQL.

---

## 2. System Architecture & High-Level Data Flow

```
                                 ┌───────────────────────────┐
                                 │   Uploaded Clinical PDF   │
                                 └─────────────┬─────────────┘
                                               │
                                               ▼
                                 ┌───────────────────────────┐
                                 │    PDF Text Extractor     │
                                 │   (pypdf / pdfplumber)    │
                                 └─────────────┬─────────────┘
                                               │
                                               ▼
                                 ┌───────────────────────────┐
                                 │ Patient Identity Verifier │
                                 │ & PHI De-identification   │
                                 └─────────────┬─────────────┘
                                               │
                                               ▼
                                 ┌───────────────────────────┐
                                 │   Groq LLM Parser &       │
                                 │ Entity Normalizer (JSON)  │
                                 └─────────────┬─────────────┘
                                               │
                                               ▼
                                 ┌───────────────────────────┐
                                 │  Fast-Track Check (No PA) │
                                 └───────┬───────────┬───────┘
                       Auto-Approved     │           │ Prior Auth Required
                                         │           ▼
                                         │   ┌───────────────────────────────┐
                                         │   │  ML Approval Risk Predictor   │
                                         │   └───────────────┬───────────────┘
                                         │                   │
                                         │                   ▼
                                         │   ┌───────────────────────────────┐
                                         │   │  Deterministic Rule Engine    │
                                         │   │ (Payer Policy Criteria Check) │
                                         │   └───────────────┬───────────────┘
                                         │                   │
                                         └───────────┬───────┘
                                                     │
                                                     ▼
                                 ┌───────────────────────────┐
                                 │ Final Decision Synthesis  │
                                 │ (APPROVED / DENIED /      │
                                 │   MANUAL_REVIEW)          │
                                 └─────────────┬─────────────┘
                                               │
                                     ┌─────────┴─────────┐
                                     ▼                   ▼
                      ┌──────────────────────┐ ┌───────────────────┐
                      │ Supabase PostgreSQL  │ │ Streamlit SaaS UI │
                      │      Database        │ │ (Clinical Portal) │
                      └──────────────────────┘ └───────────────────┘
```

---

## 3. Technology Stack

| Layer | Technologies Used | Description / Purpose |
| :--- | :--- | :--- |
| **Frontend UI** | Streamlit, Custom CSS Design System | Modern clinical SaaS dashboard with dark theme, responsive grids, metric cards, status badges, and interactive navigation. |
| **LLM & Parsing** | Groq API (`llama-3.3-70b-versatile` / `llama3-70b-8192`), Regex Fallback | Structured extraction of medical JSON schemas from unstructured clinical narratives. |
| **Document Processing** | `pypdf`, `pdfplumber` | Extracts clean raw text from uploaded patient PDF files. |
| **ML Engine** | Custom Statistical Risk Engine (`src/predictor.py`) | Predicts risk profile (Approval, Denial, Manual Review) based on clinical severity, codes, and historical weights. |
| **Rule Engine** | Deterministic Policy Evaluator (`src/rule_engine.py`) | Evaluates step-therapy, severity evidence, required documentation, and contraindications. |
| **Database** | Supabase (PostgreSQL) | Managed cloud database with 5 interconnected tables (`patients`, `authorization_requests`, `predictions`, `decisions`, `decision_criteria`). |
| **Utilities** | Python `hashlib`, `dotenv`, `logging`, `json` | In-memory SHA-256 caching for document parsing, environment management, and system auditing. |

---

## 4. End-to-End Workflow & Pipeline Details

### Step 1: Document Upload & PDF Text Extraction
- The user uploads a patient chart in PDF format via the Streamlit interface.
- `src/pdf_extractor.py` extracts raw text line-by-line using `pypdf`/`pdfplumber`.

### Step 2: Patient Identity Verification & PHI Privacy
- `src/patient_verifier.py` parses patient demographics (Full Name, Date of Birth, Gender, Patient ID).
- Calculates exact patient age dynamically from DOB.
- Performs verification checks against claim records (`name_match`, `dob_match`, `id_match`).
- Applies **local PHI de-identification** (`deidentify_text`) to sanitize sensitive health information when required.

### Step 3: LLM Clinical Entity Parsing & Normalization
- `src/patient_parser.py` computes a **SHA-256 hash** of the document text to maintain an in-memory extraction cache, avoiding redundant LLM API calls.
- Constructs a strict system prompt instructing Groq LLM to return JSON with clinical schema (Demographics, ICD-10, CPT, Severity, Step Therapy, Documentation).
- If the LLM call fails or API keys are missing, the system falls back gracefully to a **local deterministic regex parser** to ensure 100% operational uptime.
- `src/normalizer.py` standardizes diagnostic codes (ICD-10 formatting), procedure codes (CPT/HCPCS), and clinical severity ratings (`MILD`, `MODERATE`, `SEVERE`, `CRITICAL`).

### Step 4: Fast-Track Exclusion Check (`no_prior_auth`)
- `src/policy_matcher.py` & `src/decision.py` load `data/no_prior_auth.json`.
- If the requested CPT code or procedure is explicitly on the No-PA list, the request is **immediately auto-approved** with zero delay (`AUTO_APPROVED`).

### Step 5: Machine Learning Risk Assessment
- `src/predictor.py` runs an ML prediction engine to evaluate overall risk.
- Calculates probability scores: P(Approval), P(Denial), and P(Manual Review).
- Considers clinical factors such as severity score weights, prior treatment completion ratio, and diagnostic alignment.

### Step 6: Deterministic Policy Evaluation (Rule Engine)
- `src/rule_engine.py` matches the request against policy guidelines in `data/policies.json`.
- Evaluates individual clinical criteria:
  1. **Diagnosis / ICD-10 Code Match:** Validates if the procedure is indicated for the patient's condition.
  2. **Severity Threshold:** Ensures disease severity meets minimum coverage requirements.
  3. **Step Therapy / Prior Treatments:** Verifies if required conservative treatments were completed before approving major surgery.
  4. **Documentation Completeness:** Checks for required lab tests, imaging reports, and specialist recommendations.
  5. **Contraindications:** Checks for clinical red flags or conflicting conditions.

### Step 7: Final Decision Synthesis
- `src/decision.py` aggregates output from all engines:
  - **APPROVED:** All policy criteria passed + low risk score.
  - **DENIED:** One or more critical criteria failed.
  - **MANUAL_REVIEW:** Edge cases, ambiguous evidence, or high ML uncertainty.
- Produces actionable, human-readable explanations of **Passed Criteria**, **Failed Criteria**, and **Missing Evidence**.

### Step 8: Persistence & Streamlit Interface Sync
- `src/database.py` persists all results transactionally to Supabase PostgreSQL.
- Streamlit UI renders real-time status, metric highlights, clinical breakdown, and audit logs.

---

## 5. Repository Structure & Key Codebase Files

```
pre-auth/
├── app.py                      # Main Streamlit SaaS application & router
├── requirements.txt            # Python dependencies (streamlit, groq, supabase, etc.)
├── supabase_schema.sql         # Database DDL script for PostgreSQL
├── README.md                   # Complete system documentation & quick start
├── sample_patient_john_doe.pdf # Sample patient clinical document for testing
├── data/
│   ├── policies.json           # Clinical policy guidelines & criteria definitions
│   └── no_prior_auth.json      # Fast-track CPT exclusion list
└── src/
    ├── __init__.py
    ├── database.py             # Supabase PostgreSQL database client & SQL operations
    ├── decision.py             # Decision orchestration & final status synthesis
    ├── normalizer.py           # Clinical entity standardization & formatting
    ├── patient_parser.py       # Groq LLM patient extraction with SHA-256 cache & fallback
    ├── patient_verifier.py     # Identity verification, DOB calculation & PHI masking
    ├── pdf_extractor.py        # PDF document reader (pypdf/pdfplumber)
    ├── policy_matcher.py       # Policy lookup & code matching utilities
    ├── predictor.py            # ML risk prediction & probability model
    ├── rule_engine.py          # Deterministic clinical rule evaluator
    └── ui.py                   # Custom Streamlit layout, CSS styles, & view components
```

---

## 6. Database Schema (Supabase PostgreSQL)

The project includes a 5-table relational schema defined in `supabase_schema.sql`:

1. **`patients`**: Stores structured clinical data (Name, Age, Gender, Payer, ICD-10, CPT, Severity, Previous Treatments, Documentation).
2. **`authorization_requests`**: Tracks authorization lifecycle states (`PENDING`, `APPROVED`, `DENIED`, `MANUAL_REVIEW`).
3. **`predictions`**: Stores ML risk scores and class probability distributions (P_Approval, P_Denial, P_Review).
4. **`decisions`**: Stores deterministic decision results, matching policy IDs, and list of failed criteria.
5. **`decision_criteria`**: Stores granular line-item evaluations for each policy criterion (Criterion name, Required vs Provided, Pass/Fail status).

---

## 7. User Interface (UI Views)

The Streamlit UI in `src/ui.py` provides a SaaS experience with 5 primary views:

1. **📊 Executive Dashboard:** Real-time metrics showing total authorization volume, approval rates, average processing time, decision breakdown pie chart, and recent requests table.
2. **✚ Prior Auth Intake:** Interactive document uploader with progress tracker (Upload -> Verification -> LLM Extraction -> Policy Check -> Final Decision Card).
3. **📋 All Requests:** Comprehensive directory of submitted authorizations with search bar, status filter, and quick view buttons.
4. **🔎 Case View:** Deep-dive view for a specific patient displaying clinical history, step-therapy evidence timeline, criteria evaluation table, and manual override capabilities.
5. **📜 Policy Explorer:** Interactive registry allowing clinical teams to explore supported CPT codes, coverage criteria, required documentation, and rules.
6. **🛡️ Audit & System Logs:** Operational logging trail documenting every step, timestamp, document hash, and system event for HIPAA/regulatory compliance.

---

## 8. How to Setup and Run the Project

### Prerequisites
- Python 3.9+
- Groq API Key (for LLM extraction)
- (Optional) Supabase Project credentials for cloud PostgreSQL persistence

### Quick Start Guide

1. **Clone & Navigate to Directory:**
   ```bash
   cd pre-auth
   ```

2. **Install Dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure Environment Variables (`.env`):**
   Create a `.env` file in the `pre-auth` directory:
   ```env
   GROQ_API_KEY=your_groq_api_key_here
   SUPABASE_URL=your_supabase_url_here
   SUPABASE_KEY=your_supabase_anon_key_here
   ```

4. **Initialize Database (Optional):**
   Execute the contents of `supabase_schema.sql` in your Supabase SQL Editor.

5. **Launch the Application:**
   ```bash
   python -m streamlit run app.py
   ```

---

## 9. Key System Strengths & Innovations

- **Hybrid AI Architecture:** Merges generative LLM parsing (`Groq`) with deterministic safety-first clinical rules (`Rule Engine`). Generative AI handles data extraction while deterministic code makes the final medical authorization decision.
- **Resilient Fallbacks:** If the LLM API is unavailable, the local regex parser ensures continuous operation without system failure.
- **Transparency & Explainability:** Provides granular reasons for every decision, showing exactly which policy criteria passed or failed.
- **Privacy & Security:** Built-in identity verification, DOB age validation, and PHI masking.
- **Performance:** In-memory SHA-256 document hashing eliminates unnecessary API calls and speeds up re-processing.
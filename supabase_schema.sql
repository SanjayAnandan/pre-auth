-- ==============================================================================
-- Prior Authorization AI - Supabase PostgreSQL Database Schema
-- ==============================================================================

-- Enable UUID extension if not enabled
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ------------------------------------------------------------------------------
-- TABLE 1: patients
-- Purpose: Store structured clinical patient data extracted from uploaded PDFs
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS patients (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    patient_id TEXT,
    patient_name TEXT,
    age INTEGER,
    gender TEXT,
    payer TEXT,
    diagnosis TEXT,
    icd10_code TEXT,
    severity TEXT,
    severity_evidence JSONB DEFAULT '[]'::jsonb,
    previous_treatment JSONB DEFAULT '[]'::jsonb,
    previous_procedure JSONB DEFAULT '[]'::jsonb,
    requested_service TEXT,
    cpt_hcpcs_code TEXT,
    quantity TEXT,
    frequency TEXT,
    provider_specialty TEXT,
    facility_type TEXT,
    documentation JSONB DEFAULT '{}'::jsonb,
    clinical_information JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Index for searching patients by identifier or code
CREATE INDEX IF NOT EXISTS idx_patients_patient_id ON patients(patient_id);
CREATE INDEX IF NOT EXISTS idx_patients_cpt_code ON patients(cpt_hcpcs_code);
CREATE INDEX IF NOT EXISTS idx_patients_created_at ON patients(created_at DESC);

-- ------------------------------------------------------------------------------
-- TABLE 2: authorization_requests
-- Purpose: Manage prior authorization requests linked to patients
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS authorization_requests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    patient_id UUID REFERENCES patients(id) ON DELETE CASCADE,
    requested_service TEXT,
    cpt_hcpcs_code TEXT,
    quantity TEXT,
    frequency TEXT,
    payer TEXT,
    request_status TEXT NOT NULL DEFAULT 'PENDING',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Index for querying requests
CREATE INDEX IF NOT EXISTS idx_auth_requests_patient_id ON authorization_requests(patient_id);
CREATE INDEX IF NOT EXISTS idx_auth_requests_status ON authorization_requests(request_status);
CREATE INDEX IF NOT EXISTS idx_auth_requests_created_at ON authorization_requests(created_at DESC);

-- ------------------------------------------------------------------------------
-- TABLE 3: predictions
-- Purpose: Store ML risk signals and prediction probability distributions
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS predictions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    request_id UUID REFERENCES authorization_requests(id) ON DELETE CASCADE,
    model_name TEXT NOT NULL,
    model_version TEXT NOT NULL,
    predicted_class TEXT,
    approval_probability DOUBLE PRECISION,
    denial_probability DOUBLE PRECISION,
    review_probability DOUBLE PRECISION,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Index for linking predictions to authorization requests
CREATE INDEX IF NOT EXISTS idx_predictions_request_id ON predictions(request_id);

-- ------------------------------------------------------------------------------
-- TABLE 4: decisions
-- Purpose: Store final deterministic rule-engine decisions
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS decisions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    request_id UUID REFERENCES authorization_requests(id) ON DELETE CASCADE,
    policy_id TEXT,
    policy_name TEXT,
    final_decision TEXT NOT NULL,
    failed_criteria JSONB DEFAULT '[]'::jsonb,
    manual_review_reasons JSONB DEFAULT '[]'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Index for searching decisions by request and final status
CREATE INDEX IF NOT EXISTS idx_decisions_request_id ON decisions(request_id);
CREATE INDEX IF NOT EXISTS idx_decisions_final_decision ON decisions(final_decision);
CREATE INDEX IF NOT EXISTS idx_decisions_created_at ON decisions(created_at DESC);

-- ------------------------------------------------------------------------------
-- TABLE 5: decision_criteria
-- Purpose: Store individual criterion results evaluated by the rule engine
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS decision_criteria (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    decision_id UUID REFERENCES decisions(id) ON DELETE CASCADE,
    criterion TEXT NOT NULL,
    status TEXT NOT NULL,
    reason TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Index for retrieving criteria of a decision
CREATE INDEX IF NOT EXISTS idx_decision_criteria_decision_id ON decision_criteria(decision_id);
CREATE INDEX IF NOT EXISTS idx_decision_criteria_status ON decision_criteria(status);

-- ------------------------------------------------------------------------------
-- ROW LEVEL SECURITY (RLS) CONFIGURATION
-- Allow application API access
-- ------------------------------------------------------------------------------
ALTER TABLE patients DISABLE ROW LEVEL SECURITY;
ALTER TABLE authorization_requests DISABLE ROW LEVEL SECURITY;
ALTER TABLE predictions DISABLE ROW LEVEL SECURITY;
ALTER TABLE decisions DISABLE ROW LEVEL SECURITY;
ALTER TABLE decision_criteria DISABLE ROW LEVEL SECURITY;


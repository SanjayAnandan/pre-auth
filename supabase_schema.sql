-- ==============================================================================
-- Prior Authorization AI - Supabase PostgreSQL Database Schema
-- Enterprise-grade, auditable, human-readable prior authorization database.
-- ==============================================================================

-- Enable UUID extension if not enabled
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ------------------------------------------------------------------------------
-- SEQUENCES & HUMAN-READABLE REFERENCE NUMBER GENERATORS
-- ------------------------------------------------------------------------------
CREATE SEQUENCE IF NOT EXISTS patient_number_seq START WITH 1 INCREMENT BY 1;
CREATE SEQUENCE IF NOT EXISTS request_number_seq START WITH 1 INCREMENT BY 1;
CREATE SEQUENCE IF NOT EXISTS decision_number_seq START WITH 1 INCREMENT BY 1;
CREATE SEQUENCE IF NOT EXISTS document_number_seq START WITH 1 INCREMENT BY 1;

CREATE OR REPLACE FUNCTION generate_patient_number() RETURNS TEXT AS $$
BEGIN
    RETURN 'PAT-' || LPAD(nextval('patient_number_seq')::TEXT, 6, '0');
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION generate_request_number() RETURNS TEXT AS $$
BEGIN
    RETURN 'PA-' || LPAD(nextval('request_number_seq')::TEXT, 6, '0');
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION generate_decision_number() RETURNS TEXT AS $$
BEGIN
    RETURN 'DEC-' || LPAD(nextval('decision_number_seq')::TEXT, 6, '0');
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION generate_document_number() RETURNS TEXT AS $$
BEGIN
    RETURN 'DOC-' || LPAD(nextval('document_number_seq')::TEXT, 6, '0');
END;
$$ LANGUAGE plpgsql;

-- ------------------------------------------------------------------------------
-- TABLE 1: patients
-- Purpose: Store structured clinical patient data
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS patients (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    patient_number TEXT DEFAULT generate_patient_number(),
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

CREATE INDEX IF NOT EXISTS idx_patients_patient_id ON patients(patient_id);
CREATE INDEX IF NOT EXISTS idx_patients_cpt_code ON patients(cpt_hcpcs_code);
CREATE INDEX IF NOT EXISTS idx_patients_created_at ON patients(created_at DESC);

-- ------------------------------------------------------------------------------
-- TABLE 2: authorization_requests
-- Purpose: Manage prior authorization requests linked to patients
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS authorization_requests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    request_number TEXT DEFAULT generate_request_number(),
    patient_id UUID REFERENCES patients(id) ON DELETE CASCADE,
    requested_service TEXT,
    cpt_hcpcs_code TEXT,
    quantity TEXT,
    frequency TEXT,
    payer TEXT,
    request_status TEXT NOT NULL DEFAULT 'PENDING',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_auth_requests_patient_id ON authorization_requests(patient_id);
CREATE INDEX IF NOT EXISTS idx_auth_requests_status ON authorization_requests(request_status);
CREATE INDEX IF NOT EXISTS idx_auth_requests_created_at ON authorization_requests(created_at DESC);

-- ------------------------------------------------------------------------------
-- TABLE 3: documents
-- Purpose: Store document metadata and storage references
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_number TEXT DEFAULT generate_document_number(),
    request_id UUID REFERENCES authorization_requests(id) ON DELETE CASCADE,
    document_type TEXT NOT NULL,
    file_name TEXT NOT NULL,
    storage_path TEXT,
    identity_verification_status TEXT DEFAULT 'PENDING',
    processing_status TEXT DEFAULT 'PROCESSED',
    uploaded_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_documents_request_id ON documents(request_id);

-- ------------------------------------------------------------------------------
-- TABLE 4: identity_verifications
-- Purpose: Audit log of local deterministic patient document verification
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS identity_verifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    request_id UUID REFERENCES authorization_requests(id) ON DELETE CASCADE,
    identity_status TEXT NOT NULL,
    verified_fields JSONB DEFAULT '{}'::jsonb,
    mismatch_fields JSONB DEFAULT '{}'::jsonb,
    verified_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_id_verifications_request_id ON identity_verifications(request_id);

-- ------------------------------------------------------------------------------
-- TABLE 5: clinical_facts
-- Purpose: Store extracted, normalized clinical facts used for evaluation
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS clinical_facts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    request_id UUID REFERENCES authorization_requests(id) ON DELETE CASCADE,
    diagnosis TEXT,
    icd10_code TEXT,
    requested_service TEXT,
    cpt_hcpcs_code TEXT,
    severity TEXT,
    severity_evidence JSONB DEFAULT '[]'::jsonb,
    previous_treatment JSONB DEFAULT '[]'::jsonb,
    documentation JSONB DEFAULT '{}'::jsonb,
    clinical_information JSONB DEFAULT '{}'::jsonb,
    model_name TEXT DEFAULT 'Groq LLM',
    extraction_status TEXT DEFAULT 'SUCCESS',
    processed_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_clinical_facts_request_id ON clinical_facts(request_id);

-- ------------------------------------------------------------------------------
-- TABLE 6: decisions
-- Purpose: Store final deterministic rule-engine decisions
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS decisions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    decision_number TEXT DEFAULT generate_decision_number(),
    request_id UUID REFERENCES authorization_requests(id) ON DELETE CASCADE,
    policy_id TEXT,
    policy_name TEXT,
    final_decision TEXT NOT NULL,
    failed_criteria JSONB DEFAULT '[]'::jsonb,
    manual_review_reasons JSONB DEFAULT '[]'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_decisions_request_id ON decisions(request_id);
CREATE INDEX IF NOT EXISTS idx_decisions_final_decision ON decisions(final_decision);
CREATE INDEX IF NOT EXISTS idx_decisions_created_at ON decisions(created_at DESC);

-- ------------------------------------------------------------------------------
-- TABLE 7: decision_criteria
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

CREATE INDEX IF NOT EXISTS idx_decision_criteria_decision_id ON decision_criteria(decision_id);
CREATE INDEX IF NOT EXISTS idx_decision_criteria_status ON decision_criteria(status);

-- ------------------------------------------------------------------------------
-- TABLE 8: predictions (Legacy backward compatibility table)
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

-- ------------------------------------------------------------------------------
-- ROW LEVEL SECURITY (RLS) CONFIGURATION
-- Disable RLS for application service role access
-- ------------------------------------------------------------------------------
ALTER TABLE patients DISABLE ROW LEVEL SECURITY;
ALTER TABLE authorization_requests DISABLE ROW LEVEL SECURITY;
ALTER TABLE documents DISABLE ROW LEVEL SECURITY;
ALTER TABLE identity_verifications DISABLE ROW LEVEL SECURITY;
ALTER TABLE clinical_facts DISABLE ROW LEVEL SECURITY;
ALTER TABLE decisions DISABLE ROW LEVEL SECURITY;
ALTER TABLE decision_criteria DISABLE ROW LEVEL SECURITY;
ALTER TABLE predictions DISABLE ROW LEVEL SECURITY;

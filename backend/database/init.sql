-- Enable UUID generation support
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================================
-- Table: users
-- ============================================================
CREATE TABLE IF NOT EXISTS users (
    id              UUID          PRIMARY KEY DEFAULT uuid_generate_v4(),
    email           VARCHAR(255)  UNIQUE NOT NULL,
    hashed_password VARCHAR(255)  NOT NULL,
    full_name       VARCHAR(255)  NOT NULL,
    is_active       BOOLEAN       NOT NULL DEFAULT true,
    created_at      TIMESTAMPTZ   DEFAULT now(),
    updated_at      TIMESTAMPTZ   DEFAULT now()
);

-- ============================================================
-- Table: practice_jobs
-- ============================================================
CREATE TABLE IF NOT EXISTS practice_jobs (
    id          UUID         PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id     UUID         NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title       VARCHAR(255) NOT NULL,
    description TEXT         NOT NULL,
    jd_parsed   JSONB,
    created_at  TIMESTAMPTZ  DEFAULT now(),
    updated_at  TIMESTAMPTZ  DEFAULT now()
);

-- ============================================================
-- Table: practice_sessions
-- ============================================================
CREATE TABLE IF NOT EXISTS practice_sessions (
    id                   UUID         PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id              UUID         NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    job_id               UUID         NOT NULL REFERENCES practice_jobs(id) ON DELETE CASCADE,
    resume_url           VARCHAR(500),
    resume_parsed        JSONB,
    resume_report        JSONB,
    generated_questions  JSONB,
    status               VARCHAR(50)  NOT NULL DEFAULT 'parsing',
    livekit_room_name    VARCHAR(255),
    transcript           JSONB,
    interview_assessment JSONB,
    enhanced_analysis    JSONB,
    custom_additions     TEXT,
    improved_pdf_url     VARCHAR(500),
    created_at           TIMESTAMPTZ  DEFAULT now(),
    updated_at           TIMESTAMPTZ  DEFAULT now()
);

-- ============================================================
-- Migrations: add columns introduced in Phase 9
-- ============================================================
ALTER TABLE practice_sessions ADD COLUMN IF NOT EXISTS end_reason       VARCHAR(50);
ALTER TABLE practice_sessions ADD COLUMN IF NOT EXISTS duration_seconds INTEGER;

-- ============================================================
-- Indexes
-- ============================================================
CREATE INDEX IF NOT EXISTS idx_practice_jobs_user_id     ON practice_jobs(user_id);
CREATE INDEX IF NOT EXISTS idx_practice_sessions_user_id ON practice_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_practice_sessions_status  ON practice_sessions(status);

-- ============================================================
-- Seed Data: test candidate user
-- Password: "practice_password_2026" (bcrypt hash)
-- ============================================================
INSERT INTO users (id, email, hashed_password, full_name)
VALUES (
    'a1b2c3d4-e5f6-7a8b-9c0d-1e2f3a4b5c6d',
    'test.candidate@example.com',
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj4J/HS.iK8i',
    'John Practice Doe'
)
ON CONFLICT (email) DO NOTHING;

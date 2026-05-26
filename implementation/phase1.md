# Phase 1: Local PostgreSQL Infrastructure via Docker & Initialization

## 1. Objective
Establish a persistent, local PostgreSQL database instance inside Docker, create the core candidate-centric tables, and handle basic mock data seeds to test connectivity.

## 2. Docker Architecture (`docker-compose.yml`)
To mirror the architecture, create a `docker-compose.yml` file in the project root folder specifying the network, image configuration, environment variables, and persistent data volume.

```yaml
version: '3.8'

services:
  practice-db:
    image: postgres:16-alpine
    container_name: candidate_practice_postgres
    restart: unless-stopped
    environment:
      POSTGRES_USER: practice_user
      POSTGRES_PASSWORD: practice_password_2026
      POSTGRES_DB: interview_practice_db
    ports:
      - "5432:5432"
    volumes:
      - postgres_practice_data:/var/lib/postgresql/data
      - ./database/init.sql:/docker-entrypoint-initdb.d/init.sql
    networks:
      - practice-network
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U practice_user -d interview_practice_db"]
      interval: 10s
      timeout: 5s
      retries: 5

networks:
  practice-network:
    driver: bridge

volumes:
  postgres_practice_data:
    driver: local


3. Relational Schema Blueprint (database/init.sql)
This script initializes the core single-user schemas when the Docker container initializes for the first time.

-- Enable UUID extension natively in PostgreSQL
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 1. USERS TABLE (Candidate account proxy)
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    full_name VARCHAR(255) NOT NULL,
    is_active BOOLEAN DEFAULT true NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT now() NOT NULL
);

-- 2. PRACTICE JOBS TABLE (Target roles pasted by the candidate)
CREATE TABLE IF NOT EXISTS practice_jobs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,
    jd_parsed JSONB, -- Stores structure: summary, key skills, raw requirements
    created_at TIMESTAMPTZ DEFAULT now() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT now() NOT NULL
);

-- 3. PRACTICE SESSIONS TABLE (Combines applications, interviews, and metrics)
CREATE TABLE IF NOT EXISTS practice_sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    job_id UUID NOT NULL REFERENCES practice_jobs(id) ON DELETE CASCADE,
    resume_url VARCHAR(500), -- local path or local storage bucket string
    resume_parsed JSONB, -- parsed personal data, historical records, explicit lists
    resume_report JSONB, -- matching metric summaries, strengths, alignment gaps, score/100
    generated_questions JSONB, -- Encoded narrative array consisting of exactly 8 customized turns
    status VARCHAR(50) DEFAULT 'parsing' NOT NULL, -- 'parsing', 'scoring', 'ready_to_start', 'interviewing', 'completed'
    livekit_room_name VARCHAR(255),
    transcript JSONB, -- array element collection: [{"speaker": "agent/candidate", "text": "...", "created_at": ...}]
    interview_assessment JSONB, -- Multi-dimension assessment JSON score profile
    created_at TIMESTAMPTZ DEFAULT now() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT now() NOT NULL
);

-- Indexes for lightning-fast lookups on foreign keys and active statuses
CREATE INDEX IF NOT EXISTS idx_practice_jobs_user_id ON practice_jobs(user_id);
CREATE INDEX IF NOT EXISTS idx_practice_sessions_user_id ON practice_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_practice_sessions_status ON practice_sessions(status);

-- 4. SEED DATA (For validation checking)
INSERT INTO users (id, email, hashed_password, full_name)
VALUES ('a1b2c3d4-e5f6-7a8b-9c0d-1e2f3a4b5c6d', 'test.candidate@example.com', '$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36XQwXGpx6W2K3U34qD1234', 'John Practice Doe')
ON CONFLICT (email) DO NOTHING;

4. Verification Check Constraints
The Kiro agent must verify successful completion by running:

docker compose up -d practice-db

docker exec -it candidate_practice_postgres psql -U practice_user -d interview_practice_db -c "\dt"

Confirm output shows the 3 core tables: users, practice_jobs, and practice_sessions.




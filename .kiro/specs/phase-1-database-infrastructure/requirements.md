# Requirements Document

## Introduction

Phase 1 establishes the foundational local PostgreSQL database infrastructure for the Candidate Interview Practice Portal. This phase provisions a containerized PostgreSQL instance via Docker Compose, initializes the core relational schema required to support the full candidate workflow (from session creation through post-interview assessment), and seeds baseline test data to validate connectivity. All subsequent phases depend on this infrastructure being stable and correctly structured.

## Glossary

- **PostgreSQL**: The open-source relational database engine used to persist all candidate and session data.
- **Docker Compose**: The container orchestration tool used to run the PostgreSQL instance locally in an isolated, reproducible environment.
- **practice_db (Container)**: The Docker service named `practice-db` running the PostgreSQL 16 Alpine image.
- **init.sql**: The SQL initialization script mounted into the Docker container that creates all tables, indexes, and seed data on first boot.
- **UUID**: Universally Unique Identifier — the primary key type used across all tables.
- **JSONB**: PostgreSQL's binary JSON column type used to store structured LLM output payloads (parsed resume, report, questions, assessment).
- **TIMESTAMPTZ**: Timezone-aware timestamp column type used for all audit fields.
- **users**: The table representing a candidate account in the system.
- **practice_jobs**: The table storing target job descriptions pasted by the candidate.
- **practice_sessions**: The central table tracking the full lifecycle of a single interview practice attempt, including all LLM artifacts and status transitions.
- **Session Status**: An enumerated string field on `practice_sessions` tracking pipeline progress through the values: `parsing`, `scoring`, `ready_to_start`, `interviewing`, `interview_processing`, `completed`.
- **Seed Data**: A pre-inserted test user row used to validate database connectivity and support development without requiring a live authentication flow.
- **Health Check**: A Docker-native periodic command that verifies the PostgreSQL service is accepting connections before dependent services start.
- **Persistent Volume**: A named Docker volume (`postgres_practice_data`) that ensures database data survives container restarts.

---

## Requirements

### Requirement 1

**User Story:** As a developer, I want a containerized local PostgreSQL instance, so that the database environment is reproducible, isolated, and does not require a manual installation on the host machine.

#### Acceptance Criteria

1. THE Docker Compose configuration SHALL define a service named `practice-db` using the `postgres:16-alpine` image with a restart policy of `unless-stopped`.
2. THE Docker Compose configuration SHALL bind the container's PostgreSQL port to host port `5432` to allow local client connections.
3. THE Docker Compose configuration SHALL mount a named volume `postgres_practice_data` to `/var/lib/postgresql/data` inside the container to persist data across restarts.
4. THE Docker Compose configuration SHALL define a `practice-network` bridge network and attach the `practice-db` service to it.
5. THE `practice-db` service SHALL include a health check that executes `pg_isready -U practice_user -d interview_practice_db` on a 10-second interval with a 5-second timeout and 5 retries before the service is considered healthy.

---

### Requirement 2

**User Story:** As a developer, I want the database credentials and name configured via environment variables, so that sensitive values are not hardcoded and can be overridden per environment.

#### Acceptance Criteria

1. THE Docker Compose service SHALL set the environment variable `POSTGRES_USER` to `practice_user`.
2. THE Docker Compose service SHALL set the environment variable `POSTGRES_PASSWORD` to `practice_password_2026`.
3. THE Docker Compose service SHALL set the environment variable `POSTGRES_DB` to `interview_practice_db`.

---

### Requirement 3

**User Story:** As a developer, I want the database schema initialized automatically on first container boot, so that no manual SQL execution is required to set up the tables.

#### Acceptance Criteria

1. THE Docker Compose configuration SHALL mount the file `./database/init.sql` to `/docker-entrypoint-initdb.d/init.sql` inside the container so PostgreSQL executes it on first initialization.
2. THE `init.sql` script SHALL enable the `uuid-ossp` PostgreSQL extension to support `uuid_generate_v4()` as a default primary key generator.
3. THE `init.sql` script SHALL create the `users` table with columns: `id` (UUID PK), `email` (VARCHAR 255, UNIQUE, NOT NULL), `hashed_password` (VARCHAR 255, NOT NULL), `full_name` (VARCHAR 255, NOT NULL), `is_active` (BOOLEAN, DEFAULT true, NOT NULL), `created_at` (TIMESTAMPTZ, DEFAULT now()), `updated_at` (TIMESTAMPTZ, DEFAULT now()).
4. THE `init.sql` script SHALL create the `practice_jobs` table with columns: `id` (UUID PK), `user_id` (UUID FK → users.id ON DELETE CASCADE, NOT NULL), `title` (VARCHAR 255, NOT NULL), `description` (TEXT, NOT NULL), `jd_parsed` (JSONB), `created_at` (TIMESTAMPTZ), `updated_at` (TIMESTAMPTZ).
5. THE `init.sql` script SHALL create the `practice_sessions` table with columns: `id` (UUID PK), `user_id` (UUID FK → users.id ON DELETE CASCADE, NOT NULL), `job_id` (UUID FK → practice_jobs.id ON DELETE CASCADE, NOT NULL), `resume_url` (VARCHAR 500), `resume_parsed` (JSONB), `resume_report` (JSONB), `generated_questions` (JSONB), `status` (VARCHAR 50, DEFAULT `'parsing'`, NOT NULL), `livekit_room_name` (VARCHAR 255), `transcript` (JSONB), `interview_assessment` (JSONB), `created_at` (TIMESTAMPTZ), `updated_at` (TIMESTAMPTZ).
6. THE `init.sql` script SHALL use `CREATE TABLE IF NOT EXISTS` guards on all table definitions to make the script idempotent.

---

### Requirement 4

**User Story:** As a developer, I want performance indexes on high-frequency query columns, so that dashboard and status-polling queries execute efficiently as session data grows.

#### Acceptance Criteria

1. THE `init.sql` script SHALL create an index named `idx_practice_jobs_user_id` on the `user_id` column of the `practice_jobs` table.
2. THE `init.sql` script SHALL create an index named `idx_practice_sessions_user_id` on the `user_id` column of the `practice_sessions` table.
3. THE `init.sql` script SHALL create an index named `idx_practice_sessions_status` on the `status` column of the `practice_sessions` table.
4. THE `init.sql` script SHALL use `CREATE INDEX IF NOT EXISTS` guards on all index definitions to make the script idempotent.

---

### Requirement 5

**User Story:** As a developer, I want a pre-seeded test user in the database, so that all subsequent API phases can be validated without requiring a live authentication flow.

#### Acceptance Criteria

1. THE `init.sql` script SHALL insert a row into the `users` table with a fixed UUID of `a1b2c3d4-e5f6-7a8b-9c0d-1e2f3a4b5c6d`, email `test.candidate@example.com`, full name `John Practice Doe`, and a bcrypt-hashed password string.
2. THE seed insert statement SHALL use `ON CONFLICT (email) DO NOTHING` to prevent duplicate key errors on subsequent container restarts or re-runs of the script.

---

### Requirement 6

**User Story:** As a developer, I want to verify the database setup is correct after running Docker Compose, so that I can confirm all tables exist before proceeding to Phase 2.

#### Acceptance Criteria

1. WHEN the command `docker compose up -d practice-db` is executed, THE Docker engine SHALL start the `practice-db` container in detached mode without errors.
2. WHEN the command `docker exec -it candidate_practice_postgres psql -U practice_user -d interview_practice_db -c "\dt"` is executed against a running container, THE psql client SHALL return a table listing that includes `users`, `practice_jobs`, and `practice_sessions`.

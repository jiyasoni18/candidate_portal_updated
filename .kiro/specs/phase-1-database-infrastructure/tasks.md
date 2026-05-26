# Implementation Plan: Phase 1 — Local PostgreSQL Infrastructure via Docker

- [x] 1. Create the Docker Compose service definition





  - Create `docker-compose.yml` at the project root defining the `practice-db` service with `postgres:16-alpine`, container name `candidate_practice_postgres`, port binding `5432:5432`, restart policy `unless-stopped`, `practice-network` bridge network, named volume `postgres_practice_data`, and the health check command `pg_isready -U practice_user -d interview_practice_db` (interval 10s, timeout 5s, retries 5)
  - Set environment variables `POSTGRES_USER`, `POSTGRES_PASSWORD`, and `POSTGRES_DB` directly in the service definition
  - Mount `./database/init.sql` to `/docker-entrypoint-initdb.d/init.sql` and `postgres_practice_data` volume to `/var/lib/postgresql/data`
  - Declare the `practice-network` and `postgres_practice_data` volume at the top-level `networks` and `volumes` keys
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 2.1, 2.2, 2.3_

- [x] 2. Write the SQL initialization script





- [x] 2.1 Create the `database/init.sql` file with extension and table definitions


  - Create the `database/` directory and `init.sql` file
  - Add `CREATE EXTENSION IF NOT EXISTS "uuid-ossp"` at the top
  - Write `CREATE TABLE IF NOT EXISTS users` with all columns: `id` (UUID PK default uuid_generate_v4()), `email` (VARCHAR 255 UNIQUE NOT NULL), `hashed_password` (VARCHAR 255 NOT NULL), `full_name` (VARCHAR 255 NOT NULL), `is_active` (BOOLEAN DEFAULT true NOT NULL), `created_at` (TIMESTAMPTZ DEFAULT now()), `updated_at` (TIMESTAMPTZ DEFAULT now())
  - Write `CREATE TABLE IF NOT EXISTS practice_jobs` with all columns and FK `user_id → users.id ON DELETE CASCADE`
  - Write `CREATE TABLE IF NOT EXISTS practice_sessions` with all columns including all JSONB fields (`resume_parsed`, `resume_report`, `generated_questions`, `transcript`, `interview_assessment`), `status` (VARCHAR 50 DEFAULT 'parsing' NOT NULL), `livekit_room_name`, and FKs to both `users` and `practice_jobs`
  - _Requirements: 3.2, 3.3, 3.4, 3.5, 3.6_

- [x] 2.2 Add indexes and seed data to `init.sql`


  - Append `CREATE INDEX IF NOT EXISTS idx_practice_jobs_user_id ON practice_jobs(user_id)`
  - Append `CREATE INDEX IF NOT EXISTS idx_practice_sessions_user_id ON practice_sessions(user_id)`
  - Append `CREATE INDEX IF NOT EXISTS idx_practice_sessions_status ON practice_sessions(status)`
  - Append the seed `INSERT INTO users` statement with fixed UUID `a1b2c3d4-e5f6-7a8b-9c0d-1e2f3a4b5c6d`, email `test.candidate@example.com`, full name `John Practice Doe`, and the bcrypt hash string, using `ON CONFLICT (email) DO NOTHING`
  - _Requirements: 4.1, 4.2, 4.3, 4.4, 5.1, 5.2_

- [x] 2.3 Write a SQL smoke-test script to validate the schema


  - Create `database/verify.sql` that runs `\dt`, `\di`, and `SELECT id, email FROM users` to confirm tables, indexes, and seed data are present
  - _Requirements: 6.1, 6.2_

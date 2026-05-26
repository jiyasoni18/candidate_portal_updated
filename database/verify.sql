-- Smoke-test script: run after `docker compose up -d practice-db`
-- Usage (PowerShell): Get-Content database\verify.sql | docker exec -i candidate_practice_postgres psql -U practice_user -d interview_practice_db -f /dev/stdin
-- Usage (bash/cmd):   docker exec -i candidate_practice_postgres psql -U practice_user -d interview_practice_db < database/verify.sql

-- List all tables (expect: users, practice_jobs, practice_sessions)
\dt

-- List all indexes (expect: idx_practice_jobs_user_id, idx_practice_sessions_user_id, idx_practice_sessions_status)
\di

-- Confirm seed user is present
SELECT id, email FROM users;

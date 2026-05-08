-- Migration 002: Add email verification fields to users table
-- Run with:
-- & "C:\Program Files\PostgreSQL\18\bin\psql.exe" -U postgres -d repoinsight -f "path\to\this\file.sql"

ALTER TABLE users
    ADD COLUMN IF NOT EXISTS is_verified        BOOLEAN     NOT NULL DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS verification_token VARCHAR(64) NULL,
    ADD COLUMN IF NOT EXISTS token_expires_at   TIMESTAMP   NULL;

CREATE INDEX IF NOT EXISTS idx_users_verification_token ON users(verification_token);

-- Mark all existing users as verified so old accounts still work
UPDATE users SET is_verified = TRUE WHERE is_verified = FALSE;
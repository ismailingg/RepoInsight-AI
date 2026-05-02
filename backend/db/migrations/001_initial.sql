-- RepoInsight AI — Initial Schema
-- Run this manually if you prefer SQL over SQLAlchemy's create_all()
-- psql -U postgres -d repoinsight -f 001_initial.sql

-- Enable UUID generation
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ── Users ────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS users (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email         VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    created_at    TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);

-- ── API Keys ─────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS api_keys (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id       UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    provider      VARCHAR(50)  NOT NULL,
    key_type      VARCHAR(50)  NOT NULL,
    encrypted_key TEXT         NOT NULL,
    model_name    VARCHAR(100),
    created_at    TIMESTAMP DEFAULT NOW(),
    updated_at    TIMESTAMP DEFAULT NOW(),
    UNIQUE(user_id, provider, key_type)
);

CREATE INDEX IF NOT EXISTS idx_api_keys_user ON api_keys(user_id);

-- ── Repo Sessions ─────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS repo_sessions (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    repo_url        VARCHAR(500) NOT NULL,
    status          VARCHAR(50)  DEFAULT 'pending',
    chunks_count    INTEGER      DEFAULT 0,
    files_count     INTEGER      DEFAULT 0,
    vectors_count   INTEGER      DEFAULT 0,
    ingested_at     TIMESTAMP,
    collection_name VARCHAR(100),
    chat_history    JSONB        DEFAULT '[]',
    error_message   TEXT,
    created_at      TIMESTAMP DEFAULT NOW(),
    updated_at      TIMESTAMP DEFAULT NOW(),
    UNIQUE(user_id, repo_url)
);

CREATE INDEX IF NOT EXISTS idx_repo_sessions_user    ON repo_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_repo_sessions_repo    ON repo_sessions(repo_url);
CREATE INDEX IF NOT EXISTS idx_repo_sessions_status  ON repo_sessions(status);
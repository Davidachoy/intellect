-- Intellect — Supabase schema (ARCHITECTURE.md)
-- Run manually against Supabase; do not auto-migrate from this task.

CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "vector";

-- ---------------------------------------------------------------------------
-- companies
-- ---------------------------------------------------------------------------
CREATE TABLE companies (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    name            text NOT NULL,
    api_key_hash    text NOT NULL,
    created_at      timestamptz NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX companies_name_idx ON companies (name);

-- ---------------------------------------------------------------------------
-- intelligence_agents
-- ---------------------------------------------------------------------------
CREATE TABLE intelligence_agents (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id      uuid NOT NULL REFERENCES companies (id) ON DELETE CASCADE,
    config          jsonb NOT NULL DEFAULT '{}'::jsonb,
    active          boolean NOT NULL DEFAULT true,
    created_at      timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX intelligence_agents_company_id_idx ON intelligence_agents (company_id);

-- ---------------------------------------------------------------------------
-- documents (partitioned logically by company_id)
-- ---------------------------------------------------------------------------
CREATE TABLE documents (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id      uuid NOT NULL REFERENCES companies (id) ON DELETE CASCADE,
    content         text NOT NULL,
    embedding       vector(768),
    metadata        jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at      timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX documents_company_id_idx ON documents (company_id);
CREATE INDEX documents_metadata_gin_idx ON documents USING gin (metadata);

-- ---------------------------------------------------------------------------
-- queries
-- ---------------------------------------------------------------------------
CREATE TABLE queries (
    id                      uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    querier_api_key_hash    text NOT NULL,
    target_company_id       uuid NOT NULL REFERENCES companies (id) ON DELETE CASCADE,
    raw_query               text NOT NULL,
    structured_query        jsonb,
    response                text,
    blocked                 boolean NOT NULL DEFAULT false,
    block_reason            text,
    cost_usd                numeric(10, 6),
    record_count            int,
    created_at              timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX queries_target_company_id_idx ON queries (target_company_id);
CREATE INDEX queries_created_at_idx ON queries (created_at DESC);

-- ---------------------------------------------------------------------------
-- audit_log
-- ---------------------------------------------------------------------------
CREATE TABLE audit_log (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    query_id        uuid NOT NULL REFERENCES queries (id) ON DELETE CASCADE,
    agent           text NOT NULL,
    event           text NOT NULL,
    payload         jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at      timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX audit_log_query_id_idx ON audit_log (query_id);
CREATE INDEX audit_log_created_at_idx ON audit_log (created_at DESC);

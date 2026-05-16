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

-- ---------------------------------------------------------------------------
-- anomaly_alerts (Anomaly Detection Agent)
-- ---------------------------------------------------------------------------
CREATE TABLE anomaly_alerts (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    querier_id      text NOT NULL,
    pattern         text NOT NULL,
    query_ids       uuid[] NOT NULL DEFAULT '{}',
    severity        text NOT NULL CHECK (severity IN ('low', 'medium', 'high')),
    acknowledged    boolean NOT NULL DEFAULT false,
    created_at      timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX anomaly_alerts_created_at_idx ON anomaly_alerts (created_at DESC);
CREATE INDEX anomaly_alerts_querier_id_idx ON anomaly_alerts (querier_id);

-- ---------------------------------------------------------------------------
-- Intelligence Agent — pgvector match + aggregate-only SQL (no SELECT *)
-- ---------------------------------------------------------------------------

CREATE OR REPLACE FUNCTION metadata_matches_filters(
    meta jsonb,
    filters jsonb
)
RETURNS boolean
LANGUAGE sql
IMMUTABLE
AS $$
    SELECT
        (NOT filters ? 'region' OR meta->>'region' = filters->>'region')
        AND (NOT filters ? 'status' OR meta->>'status' = filters->>'status')
        AND (NOT filters ? 'segment' OR meta->>'segment' = filters->>'segment')
        AND (NOT filters ? 'age_range' OR meta->>'age_range' = filters->>'age_range')
        AND (NOT filters ? 'outcome' OR meta->>'outcome' = filters->>'outcome')
        AND (NOT filters ? 'cohort' OR meta->>'cohort' = filters->>'cohort')
        AND (NOT filters ? 'carrier_lane' OR meta->>'carrier_lane' = filters->>'carrier_lane')
        AND (NOT filters ? 'record_type' OR meta->>'record_type' = filters->>'record_type');
$$;

CREATE OR REPLACE FUNCTION match_company_documents(
    p_company_id uuid,
    query_embedding vector(768),
    match_count int DEFAULT 200
)
RETURNS TABLE (
    document_id uuid,
    distance double precision
)
LANGUAGE sql
STABLE
AS $$
    SELECT
        d.id AS document_id,
        (d.embedding <=> query_embedding)::double precision AS distance
    FROM documents d
    WHERE d.company_id = p_company_id
      AND d.embedding IS NOT NULL
    ORDER BY d.embedding <=> query_embedding
    LIMIT GREATEST(match_count, 1);
$$;

CREATE OR REPLACE FUNCTION intelligence_aggregate(
    p_company_id uuid,
    p_aggregation text,
    p_filters jsonb DEFAULT '{}'::jsonb,
    p_metric_field text DEFAULT 'ltv_usd',
    p_scope_ids uuid[] DEFAULT NULL
)
RETURNS jsonb
LANGUAGE plpgsql
STABLE
AS $$
DECLARE
    result jsonb;
    metric_key text := COALESCE(NULLIF(trim(p_metric_field), ''), 'ltv_usd');
BEGIN
    IF p_aggregation = 'count' THEN
        SELECT jsonb_build_object(
            'aggregation', 'count',
            'record_count', COUNT(*)::int,
            'filters', p_filters
        )
        INTO result
        FROM documents d
        WHERE d.company_id = p_company_id
          AND (p_scope_ids IS NULL OR d.id = ANY(p_scope_ids))
          AND metadata_matches_filters(d.metadata, p_filters);

    ELSIF p_aggregation = 'average' THEN
        SELECT jsonb_build_object(
            'aggregation', 'average',
            'metric', metric_key,
            'value', ROUND(AVG((d.metadata->>metric_key)::numeric), 2),
            'record_count', COUNT(*)::int,
            'filters', p_filters
        )
        INTO result
        FROM documents d
        WHERE d.company_id = p_company_id
          AND (p_scope_ids IS NULL OR d.id = ANY(p_scope_ids))
          AND metadata_matches_filters(d.metadata, p_filters)
          AND (d.metadata ? metric_key);

    ELSIF p_aggregation = 'percentage' THEN
        WITH scoped AS (
            SELECT d.metadata
            FROM documents d
            WHERE d.company_id = p_company_id
              AND (p_scope_ids IS NULL OR d.id = ANY(p_scope_ids))
        ),
        numerator AS (
            SELECT COUNT(*)::int AS cnt
            FROM scoped s
            WHERE metadata_matches_filters(s.metadata, p_filters)
        ),
        denominator AS (
            SELECT COUNT(*)::int AS cnt FROM scoped
        )
        SELECT jsonb_build_object(
            'aggregation', 'percentage',
            'value', CASE
                WHEN (SELECT cnt FROM denominator) = 0 THEN 0
                ELSE ROUND(
                    100.0 * (SELECT cnt FROM numerator)::numeric
                    / (SELECT cnt FROM denominator)::numeric,
                    2
                )
            END,
            'record_count', (SELECT cnt FROM numerator),
            'denominator_count', (SELECT cnt FROM denominator),
            'filters', p_filters
        )
        INTO result;

    ELSIF p_aggregation IN ('group_by_region', 'group_by') THEN
        SELECT jsonb_build_object(
            'aggregation', 'group_by_region',
            'groups', COALESCE(
                jsonb_agg(
                    jsonb_build_object(
                        'region', g.region,
                        'record_count', g.cnt
                    )
                    ORDER BY g.cnt DESC
                ),
                '[]'::jsonb
            ),
            'record_count', COALESCE(SUM(g.cnt), 0)::int,
            'filters', p_filters
        )
        INTO result
        FROM (
            SELECT
                d.metadata->>'region' AS region,
                COUNT(*)::int AS cnt
            FROM documents d
            WHERE d.company_id = p_company_id
              AND (p_scope_ids IS NULL OR d.id = ANY(p_scope_ids))
              AND metadata_matches_filters(d.metadata, p_filters)
              AND d.metadata ? 'region'
            GROUP BY d.metadata->>'region'
        ) AS g;

    ELSE
        RAISE EXCEPTION 'Unsupported aggregation: %', p_aggregation;
    END IF;

    RETURN COALESCE(result, '{}'::jsonb);
END;
$$;

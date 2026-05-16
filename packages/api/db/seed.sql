-- Intellect — demo seed data (3 companies, synthetic records in documents)
-- Embeddings are NULL until TASK-016 (seed_vectors.py).

-- Fixed company UUIDs for reproducible demos and tests
-- Acme Retail:        a0000000-0000-4000-8000-000000000001
-- NordLogistics:      a0000000-0000-4000-8000-000000000002
-- MedResearch:        a0000000-0000-4000-8000-000000000003

-- Demo API key hashes (SHA-256 hex of plaintext keys — not real secrets)
-- Acme: demo-key (TASK-009 curl) or acme-querier-demo
-- Nord: nord-querier-demo / Med: med-querier-demo

INSERT INTO companies (id, name, api_key_hash) VALUES
    (
        'a0000000-0000-4000-8000-000000000001',
        'Acme Retail',
        'c48a01f49fd0f2cc404bc3cbbc80e91457a3d41bb429a695243de4c61794155c'
    ),
    (
        'a0000000-0000-4000-8000-000000000002',
        'NordLogistics',
        'e40174e722b242356d57f450f620d7a10933fef07ca5b1485bcf6ddc0685953c'
    ),
    (
        'a0000000-0000-4000-8000-000000000003',
        'MedResearch',
        '308c02223d058682bbf15360dfb1fcc156b186cdb87e81dc9c9d493a9bcc0b5b'
    );

INSERT INTO intelligence_agents (id, company_id, config, active) VALUES
    (
        'b1000000-0000-4000-8000-000000000001',
        'a0000000-0000-4000-8000-000000000001',
        '{
            "domain": "retail_customers",
            "default_sensitivity_tier": "sensitive",
            "allowed_aggregations": ["count", "average", "percentage", "group_by_region"],
            "access_rules": {
                "public_fields": ["region", "segment", "status"],
                "restricted_fields": ["ltv_usd"]
            }
        }'::jsonb,
        true
    ),
    (
        'b1000000-0000-4000-8000-000000000002',
        'a0000000-0000-4000-8000-000000000002',
        '{
            "domain": "logistics_shipments",
            "default_sensitivity_tier": "aggregated",
            "allowed_aggregations": ["count", "average", "sum", "group_by_region"],
            "access_rules": {
                "public_fields": ["region", "status"],
                "restricted_fields": ["value_usd"]
            }
        }'::jsonb,
        true
    ),
    (
        'b1000000-0000-4000-8000-000000000003',
        'a0000000-0000-4000-8000-000000000003',
        '{
            "domain": "clinical_trials",
            "default_sensitivity_tier": "strategic",
            "allowed_aggregations": ["count", "percentage", "group_by_region"],
            "access_rules": {
                "public_fields": ["region", "age_range", "outcome"],
                "restricted_fields": []
            }
        }'::jsonb,
        true
    );

-- ---------------------------------------------------------------------------
-- Acme Retail — 1000 synthetic customer records (no PII)
-- Fields: age, region, segment, ltv_usd, status
-- ---------------------------------------------------------------------------
INSERT INTO documents (company_id, content, metadata)
SELECT
    'a0000000-0000-4000-8000-000000000001'::uuid,
    format(
        'Retail customer profile: age %s, region %s, segment %s, status %s, lifetime_value_usd %s',
        age,
        region,
        segment,
        status,
        ltv_usd
    ),
    jsonb_build_object(
        'record_type', 'customer',
        'age', age,
        'region', region,
        'segment', segment,
        'status', status,
        'ltv_usd', ltv_usd
    )
FROM (
    SELECT
        gs,
        18 + (gs % 63) AS age,
        (ARRAY[
            'Italy', 'France', 'Germany', 'Spain', 'UK',
            'Netherlands', 'Poland', 'Sweden', 'Portugal', 'Belgium'
        ])[1 + (gs % 10)] AS region,
        (ARRAY['enterprise', 'mid_market', 'smb', 'consumer'])[1 + (gs % 4)] AS segment,
        CASE WHEN gs % 7 = 0 THEN 'inactive' ELSE 'active' END AS status,
        round((100 + (gs % 50) * 97.5 + (gs % 13) * 12.3)::numeric, 2) AS ltv_usd
    FROM generate_series(1, 1000) AS gs
) AS acme_rows;

-- ---------------------------------------------------------------------------
-- NordLogistics — 500 synthetic shipment records
-- Fields: region, status, value_usd, carrier_lane
-- ---------------------------------------------------------------------------
INSERT INTO documents (company_id, content, metadata)
SELECT
    'a0000000-0000-4000-8000-000000000002'::uuid,
    format(
        'Shipment record: region %s, status %s, value_usd %s, carrier_lane %s',
        region,
        status,
        value_usd,
        carrier_lane
    ),
    jsonb_build_object(
        'record_type', 'shipment',
        'region', region,
        'status', status,
        'value_usd', value_usd,
        'carrier_lane', carrier_lane
    )
FROM (
    SELECT
        gs,
        (ARRAY[
            'Nordics', 'Baltics', 'DACH', 'Benelux', 'UK & Ireland',
            'Southern Europe', 'Central Europe'
        ])[1 + (gs % 7)] AS region,
        (ARRAY['in_transit', 'delivered', 'delayed', 'customs_hold', 'cancelled'])[1 + (gs % 5)] AS status,
        round((250 + (gs % 40) * 185.5 + (gs % 9) * 42.7)::numeric, 2) AS value_usd,
        (ARRAY['Oslo-Hamburg', 'Stockholm-Rotterdam', 'Helsinki-Tallinn', 'Copenhagen-Antwerp'])[1 + (gs % 4)] AS carrier_lane
    FROM generate_series(1, 500) AS gs
) AS nord_rows;

-- ---------------------------------------------------------------------------
-- MedResearch — 300 synthetic trial participant records
-- Fields: age_range, outcome, region, cohort
-- ---------------------------------------------------------------------------
INSERT INTO documents (company_id, content, metadata)
SELECT
    'a0000000-0000-4000-8000-000000000003'::uuid,
    format(
        'Trial participant: age_range %s, outcome %s, region %s, cohort %s',
        age_range,
        outcome,
        region,
        cohort
    ),
    jsonb_build_object(
        'record_type', 'trial_participant',
        'age_range', age_range,
        'outcome', outcome,
        'region', region,
        'cohort', cohort
    )
FROM (
    SELECT
        gs,
        (ARRAY['18-30', '31-45', '46-60', '61-75'])[1 + (gs % 4)] AS age_range,
        (ARRAY['improved', 'stable', 'adverse', 'withdrawn'])[1 + (gs % 4)] AS outcome,
        (ARRAY['North America', 'Western Europe', 'Eastern Europe', 'Asia-Pacific'])[1 + (gs % 4)] AS region,
        (ARRAY['Phase II-A', 'Phase II-B', 'Phase III'])[1 + (gs % 3)] AS cohort
    FROM generate_series(1, 300) AS gs
) AS med_rows;

-- Anomaly Detection Agent alerts table
CREATE TABLE IF NOT EXISTS anomaly_alerts (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    querier_id      text NOT NULL,
    pattern         text NOT NULL,
    query_ids       uuid[] NOT NULL DEFAULT '{}',
    severity        text NOT NULL CHECK (severity IN ('low', 'medium', 'high')),
    acknowledged    boolean NOT NULL DEFAULT false,
    created_at      timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS anomaly_alerts_created_at_idx ON anomaly_alerts (created_at DESC);
CREATE INDEX IF NOT EXISTS anomaly_alerts_querier_id_idx ON anomaly_alerts (querier_id);

ALTER PUBLICATION supabase_realtime ADD TABLE anomaly_alerts;

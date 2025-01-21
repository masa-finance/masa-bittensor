-- State snapshot tables
CREATE TABLE IF NOT EXISTS ops_state_snapshots (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP WITHOUT TIME ZONE NOT NULL,
    step INTEGER NOT NULL,
    scores FLOAT[] NOT NULL,
    UNIQUE(step)
);

CREATE TABLE IF NOT EXISTS ops_hotkeys (
    id SERIAL PRIMARY KEY,
    snapshot_id INTEGER REFERENCES ops_state_snapshots(id),
    position INTEGER NOT NULL,
    hotkey TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS ops_volumes (
    id SERIAL PRIMARY KEY,
    snapshot_id INTEGER REFERENCES ops_state_snapshots(id),
    position INTEGER NOT NULL,
    volume_data JSONB NOT NULL
);

CREATE TABLE IF NOT EXISTS ops_tweet_sets (
    id SERIAL PRIMARY KEY,
    snapshot_id INTEGER REFERENCES ops_state_snapshots(id),
    uid INTEGER NOT NULL,
    tweet_ids TEXT[] NOT NULL
);

-- Weight monitoring tables
CREATE TABLE IF NOT EXISTS ops_validator_weight_sets (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP WITHOUT TIME ZONE NOT NULL,
    success BOOLEAN NOT NULL,
    error_message TEXT
);

CREATE TABLE IF NOT EXISTS ops_validator_weight_details (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP WITHOUT TIME ZONE NOT NULL,
    uid INTEGER NOT NULL,
    raw_weight FLOAT NOT NULL,
    normalized_weight FLOAT NOT NULL
);

-- Indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_state_snapshots_timestamp ON ops_state_snapshots(timestamp);
CREATE INDEX IF NOT EXISTS idx_tweet_sets_uid ON ops_tweet_sets(uid);
CREATE INDEX IF NOT EXISTS idx_weight_sets_timestamp ON ops_validator_weight_sets(timestamp);
CREATE INDEX IF NOT EXISTS idx_weight_details_timestamp ON ops_validator_weight_details(timestamp);
CREATE INDEX IF NOT EXISTS idx_weight_details_uid ON ops_validator_weight_details(uid);

-- Function to clean up old snapshots
CREATE OR REPLACE FUNCTION cleanup_old_snapshots(retention_days INTEGER)
RETURNS void AS $$
BEGIN
    DELETE FROM ops_tweet_sets
    WHERE snapshot_id IN (
        SELECT id FROM ops_state_snapshots
        WHERE timestamp < NOW() - (retention_days || ' days')::INTERVAL
    );
    
    DELETE FROM ops_volumes
    WHERE snapshot_id IN (
        SELECT id FROM ops_state_snapshots
        WHERE timestamp < NOW() - (retention_days || ' days')::INTERVAL
    );
    
    DELETE FROM ops_hotkeys
    WHERE snapshot_id IN (
        SELECT id FROM ops_state_snapshots
        WHERE timestamp < NOW() - (retention_days || ' days')::INTERVAL
    );
    
    DELETE FROM ops_state_snapshots
    WHERE timestamp < NOW() - (retention_days || ' days')::INTERVAL;
END;
$$ LANGUAGE plpgsql; 
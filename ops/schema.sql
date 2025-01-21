-- Schema for storing validator state snapshots

-- Main table for state snapshots
CREATE TABLE IF NOT EXISTS ops_state_snapshots (
    id BIGSERIAL PRIMARY KEY,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    step INTEGER NOT NULL,
    scores FLOAT[] NOT NULL,  -- Array of 256 scores
    UNIQUE (step)  -- Each step should only be stored once
);

-- Table for hotkeys (references state_snapshots)
CREATE TABLE IF NOT EXISTS ops_hotkeys (
    snapshot_id BIGINT REFERENCES ops_state_snapshots(id) ON DELETE CASCADE,
    position INTEGER NOT NULL CHECK (position >= 0 AND position < 256),
    hotkey TEXT NOT NULL,
    PRIMARY KEY (snapshot_id, position)
);

-- Table for trading volumes
CREATE TABLE IF NOT EXISTS ops_volumes (
    snapshot_id BIGINT REFERENCES ops_state_snapshots(id) ON DELETE CASCADE,
    position INTEGER NOT NULL CHECK (position >= 0 AND position < 6),
    volume_data JSONB NOT NULL,  -- Store volume dict as JSON
    PRIMARY KEY (snapshot_id, position)
);

-- Table for tweet sets by UID
CREATE TABLE IF NOT EXISTS ops_tweet_sets (
    snapshot_id BIGINT REFERENCES ops_state_snapshots(id) ON DELETE CASCADE,
    uid INTEGER NOT NULL CHECK (uid >= 0 AND uid < 256),
    tweet_ids BIGINT[] NOT NULL,  -- Array of tweet IDs
    PRIMARY KEY (snapshot_id, uid)
);

-- Indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_ops_state_snapshots_timestamp ON ops_state_snapshots(timestamp);
CREATE INDEX IF NOT EXISTS idx_ops_tweet_sets_uid ON ops_tweet_sets(uid);

-- Function to clean up old snapshots
CREATE OR REPLACE FUNCTION cleanup_old_snapshots(days_to_keep INTEGER)
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    WITH deleted AS (
        DELETE FROM ops_state_snapshots
        WHERE timestamp < (CURRENT_TIMESTAMP - (days_to_keep || ' days')::INTERVAL)
        RETURNING id
    )
    SELECT COUNT(*) INTO deleted_count FROM deleted;
    
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql; 
#!/usr/bin/env python3
import os
import torch
import psycopg2
import psycopg2.extras
from datetime import datetime
import shutil

# Configuration
STATE_FILE = (
    "/home/ubuntu/.bittensor/miners/validator/default/netuid42/validator/state.pt"
)
TEMP_DIR = "/home/ubuntu/state_backups/temp"
DB_NAME = "masa"
DB_USER = "ubuntu"
DB_HOST = "localhost"


def get_db_connection():
    """Get a connection to the PostgreSQL database"""
    return psycopg2.connect(dbname=DB_NAME, user=DB_USER, host=DB_HOST)


def store_state(conn, state_file):
    """Store the state file in the database"""
    # Load state from file
    state = torch.load(state_file)

    # Start transaction
    with conn.cursor() as cur:
        try:
            # Insert main snapshot and get ID
            cur.execute(
                """
                INSERT INTO ops_state_snapshots (step, scores)
                VALUES (%s, %s)
                RETURNING id
            """,
                (state["step"], state["scores"].numpy().tolist()),
            )
            snapshot_id = cur.fetchone()[0]

            # Store hotkeys
            psycopg2.extras.execute_values(
                cur,
                """
                INSERT INTO ops_hotkeys (snapshot_id, position, hotkey)
                VALUES %s
            """,
                [(snapshot_id, i, hotkey) for i, hotkey in enumerate(state["hotkeys"])],
            )

            # Store volumes
            psycopg2.extras.execute_values(
                cur,
                """
                INSERT INTO ops_volumes (snapshot_id, position, volume_data)
                VALUES %s
            """,
                [
                    (snapshot_id, i, psycopg2.extras.Json(volume))
                    for i, volume in enumerate(state["volumes"])
                ],
            )

            # Store tweet sets
            psycopg2.extras.execute_values(
                cur,
                """
                INSERT INTO ops_tweet_sets (snapshot_id, uid, tweet_ids)
                VALUES %s
            """,
                [
                    (snapshot_id, uid, list(tweets))
                    for uid, tweets in state["tweets_by_uid"].items()
                ],
            )

            # Commit transaction
            conn.commit()
            print(
                f"Successfully stored state snapshot {snapshot_id} (step {state['step']})"
            )

        except Exception as e:
            conn.rollback()
            print(f"Error storing state: {e}")
            raise


def backup_and_store():
    """Create a temporary copy of state file and store it in the database"""
    # Ensure temp directory exists
    os.makedirs(TEMP_DIR, exist_ok=True)

    # Create temporary copy of state file
    temp_state = os.path.join(
        TEMP_DIR, f"state_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pt"
    )
    try:
        # Copy state file to temp location
        shutil.copy2(STATE_FILE, temp_state)

        # Store in database
        with get_db_connection() as conn:
            store_state(conn, temp_state)

    finally:
        # Clean up temp file
        if os.path.exists(temp_state):
            os.remove(temp_state)


if __name__ == "__main__":
    backup_and_store()

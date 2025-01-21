#!/usr/bin/env python3
import re
import psycopg2
import boto3

# AWS Configuration
boto3.setup_default_session(region_name="us-east-1")

# Fixed paths on validator
SYSLOG = "/var/log/syslog"

# Get database URLs from AWS Secrets Manager
client = boto3.client("secretsmanager")
mon_secret = client.get_secret_value(SecretId="masa/monitor/dev_mon_db")
api_secret = client.get_secret_value(SecretId="masa/monitor/api_db")
MON_DB = mon_secret["SecretString"]
API_DB = api_secret["SecretString"]


def connect_to_db(db_url):
    print("Connecting to database...")
    return psycopg2.connect(db_url)


def ensure_tables(conn):
    print("Ensuring tables exist...")
    with conn.cursor() as cur:
        # Create tables if they don't exist
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS ops_validator_weight_sets (
                id SERIAL PRIMARY KEY,
                timestamp TIMESTAMP WITHOUT TIME ZONE,
                success BOOLEAN,
                error_message TEXT
            )
        """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS ops_validator_weight_details (
                id SERIAL PRIMARY KEY,
                timestamp TIMESTAMP WITHOUT TIME ZONE,
                uid INTEGER,
                raw_weight FLOAT,
                normalized_weight FLOAT
            )
        """
        )
        conn.commit()


def parse_weights_from_line(line):
    print(f"Parsing line: {line}")
    # Extract weights and UIDs
    weights_match = re.search(
        r"Setting weights: \[([\d\., ]+)\] for uids: \[([\d\., ]+)\]", line
    )
    if not weights_match:
        # Try alternate format
        weights_match = re.search(
            r"Setting weights for subnet #42.*\[([\d\., ]+)\] for uids: \[([\d\., ]+)\]",
            line,
        )
        if not weights_match:
            print("No weights found in line")
            return None

    weights_str = weights_match.group(1)
    uids_str = weights_match.group(2)

    raw_weights = [float(w) for w in weights_str.split(",")]
    uids = [int(u) for u in uids_str.split(",")]

    # Normalize weights
    total = sum(raw_weights)
    if total == 0:
        print("Total weights sum to 0")
        return None

    normalized = [w / total for w in raw_weights]
    print(f"Found {len(uids)} weights")
    return list(zip(uids, raw_weights, normalized))


def process_database():
    print("Starting weight monitoring...")
    mon_conn = connect_to_db(MON_DB)
    api_conn = connect_to_db(API_DB)

    try:
        ensure_tables(mon_conn)
        ensure_tables(api_conn)

        print("Reading syslog...")
        # Read all lines into memory to handle looking at previous line
        with open(SYSLOG) as f:
            lines = f.readlines()

        print(f"Processing {len(lines)} lines...")
        for i in range(1, len(lines)):
            line = lines[i]

            if "set_weights on chain successfully" in line:
                print("\nFound successful weight setting")
                # Extract timestamp from success line
                ts_match = re.search(r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})", line)
                if not ts_match:
                    continue
                timestamp = ts_match.group(1)
                print(f"Timestamp: {timestamp}")

                # Look back up to 5 lines for weight setting
                for j in range(max(0, i - 5), i):
                    weights = parse_weights_from_line(lines[j])
                    if weights:
                        print(f"Storing {len(weights)} weight values...")
                        # Record successful weight setting
                        with mon_conn.cursor() as cur:
                            cur.execute(
                                "INSERT INTO ops_validator_weight_sets (timestamp, success) VALUES (%s, %s)",
                                (timestamp, True),
                            )
                            # Store individual weights
                            for uid, raw, norm in weights:
                                cur.execute(
                                    """INSERT INTO ops_validator_weight_details 
                                       (timestamp, uid, raw_weight, normalized_weight)
                                       VALUES (%s, %s, %s, %s)""",
                                    (timestamp, uid, raw, norm),
                                )
                        with api_conn.cursor() as cur:
                            cur.execute(
                                "INSERT INTO ops_validator_weight_sets (timestamp, success) VALUES (%s, %s)",
                                (timestamp, True),
                            )
                            for uid, raw, norm in weights:
                                cur.execute(
                                    """INSERT INTO ops_validator_weight_details
                                       (timestamp, uid, raw_weight, normalized_weight)
                                       VALUES (%s, %s, %s, %s)""",
                                    (timestamp, uid, raw, norm),
                                )
                        mon_conn.commit()
                        api_conn.commit()
                        print("Weight values stored successfully")
                        break

    finally:
        mon_conn.close()
        api_conn.close()


if __name__ == "__main__":
    process_database()

#!/usr/bin/env python3
import boto3
import psycopg2


def main():
    print("Starting process_weights.py")
    print("Getting database URLs from secrets...")
    client = boto3.client("secretsmanager")

    # Get monitoring DB URL
    print("Retrieving monitoring DB URL...")
    mon_secret = client.get_secret_value(SecretId="masa/monitor/dev_mon_db")
    mon_db_url = mon_secret["SecretString"]
    print("Successfully retrieved monitoring DB URL")

    # Get API DB URL
    print("Retrieving API DB URL...")
    api_secret = client.get_secret_value(SecretId="masa/monitor/api_db")
    api_db_url = api_secret["SecretString"]
    print("Successfully retrieved API DB URL")

    print("Connecting to databases...")
    # Connect to both DBs
    mon_conn = psycopg2.connect(mon_db_url)
    api_conn = psycopg2.connect(api_db_url)
    print("Successfully connected to both databases")

    try:
        # Test monitoring DB
        with mon_conn:  # This handles commit/rollback
            with mon_conn.cursor() as cur:
                cur.execute("SELECT 1")
                print("Successfully tested monitoring DB connection")

        # Test API DB
        with api_conn:  # This handles commit/rollback
            with api_conn.cursor() as cur:
                cur.execute("SELECT 1")
                print("Successfully tested API DB connection")

    finally:
        mon_conn.close()
        api_conn.close()
        print("Closed all database connections")


if __name__ == "__main__":
    main()

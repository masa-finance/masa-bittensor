#!/bin/bash

DB_NAME="bittensor_nodes.db"

create_database() {
    sqlite3 $DB_NAME <<EOF
CREATE TABLE IF NOT EXISTS nodes (
    netuid INTEGER,
    uid INTEGER,
    stake REAL,
    rank REAL,
    trust REAL,
    consensus REAL,
    incentive REAL,
    dividends REAL,
    emission INTEGER,
    vtrust REAL,
    validator INTEGER,
    updated INTEGER,
    active INTEGER,
    ip_port TEXT,
    hotkey TEXT,
    coldkey TEXT,
    timestamp TIMESTAMP,
    PRIMARY KEY (netuid, hotkey, timestamp)
);
CREATE INDEX IF NOT EXISTS idx_nodes_hotkey ON nodes(hotkey);
EOF
    echo "Database created successfully."
}

strip_control_chars() {
    tr -cd '\11\12\15\40-\176'
}

parse_and_insert_data() {
    local netuid=$1
    local timestamp=$(date +"%Y-%m-%d %H:%M:%S")
    echo "Processing netuid: $netuid"
    /opt/anaconda3/bin/btcli subnet metagraph --netuid "$netuid" | strip_control_chars | 
    awk -v netuid="$netuid" -v timestamp="$timestamp" -v db_name="$DB_NAME" '
    /UID/ { header=1; next }
    header && NF == 16 {
        uid = $1
        stake = $2
        rank = $3
        trust = $4
        consensus = $5
        incentive = $6
        dividends = $7
        emission = $8
        vtrust = $9
        validator = ($10 == "*" ? 1 : 0)
        updated = $11
        active = $12
        ip_port = $13
        hotkey = $14
        coldkey = $15

        cmd = sprintf("sqlite3 %s \"INSERT OR REPLACE INTO nodes VALUES (%d, %d, %f, %f, %f, %f, %f, %f, %d, %f, %d, %d, %d, \x27%s\x27, \x27%s\x27, \x27%s\x27, \x27%s\x27);\"", 
                      db_name, netuid, uid, stake, rank, trust, consensus, incentive, dividends, emission, vtrust, 
                      validator, updated, active, ip_port, hotkey, coldkey, timestamp)
        system(cmd)
        print "Inserted data for UID:", uid, "Hotkey:", hotkey, "IP:Port:", ip_port
    }'
}

echo "Starting Bittensor node scraper..."
create_database

while true; do
    echo "Fetching list of netuids..."
    netuids=$(/opt/anaconda3/bin/btcli subnets list | strip_control_chars | awk 'NR>2 && /^[[:space:]]*[0-9]+/ {print $1}')
    
    echo "Found netuids: $netuids"
    if [ -z "$netuids" ]; then
        echo "No netuids found. Check if btcli is working correctly."
    else
        for netuid in $netuids; do
            parse_and_insert_data "$netuid"
        done
    fi
    echo "Data processing completed at $(date)"
    echo "Waiting for 60 seconds before next update..."
    sleep 60
done

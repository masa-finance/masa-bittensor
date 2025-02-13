#!/usr/bin/env python3
import boto3
import psycopg2
import bittensor as bt
import numpy as np
from typing import Tuple, List, Dict, Optional
import sys
import os
import requests
import argparse
from datetime import datetime


def display_weight_set(uids: np.ndarray, weights: np.ndarray, timestamp: str = None):
    """Display first 5 and last 5 weights in a weight set."""
    if timestamp:
        print(f"\nWeight set from: {timestamp}")
    print("-" * 60)
    print(f"{'UID':<10} {'Weight':<15} {'Position':<10}")
    print("-" * 60)

    # Sort by weight value
    indices = np.argsort(weights)[::-1]
    sorted_uids = uids[indices]
    sorted_weights = weights[indices]

    total = len(uids)

    # Show first 5
    for i in range(min(5, total)):
        print(
            f"{sorted_uids[i]:<10} {sorted_weights[i]:<15.6f} {'Top ' + str(i+1):<10}"
        )

    if total > 10:  # If we have more than 10 items, add separator
        print("..." + " " * 57)

    # Show last 5
    if total > 5:
        start_idx = max(5, total - 5)
        for i in range(start_idx, total):
            print(
                f"{sorted_uids[i]:<10} {sorted_weights[i]:<15.6f} {'Last ' + str(total-i):<10}"
            )

    print("-" * 60)
    print(f"Total UIDs: {total}")
    print(f"Sum of weights: {weights.sum():.6f}")
    print("-" * 60)


def get_taostats_weights(
    hotkey: str, api_key: str
) -> Optional[Tuple[np.ndarray, np.ndarray]]:
    """Get historical weights from Taostats API for a specific validator hotkey."""
    print("\nFetching historical weights from Taostats API...")
    url = "https://api.taostats.io/api/validator/weights/history/v1"
    headers = {"X-API-KEY": api_key}
    params = {"hotkey": hotkey, "limit": 10}  # Get last 10 weight settings

    try:
        print(f"Requesting data for hotkey: {hotkey}")
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        data = response.json()

        if not data:
            raise Exception("No weight history found for this validator")

        print(f"\nFound {len(data)} historical weight sets")

        # Process each weight set
        for weight_set in data:
            weights_data = weight_set.get("weights", {})
            if not weights_data:
                print(
                    f"Skipping empty weight set from {weight_set.get('timestamp', 'unknown time')}"
                )
                continue

            # Convert weights dict to arrays
            uids = []
            weights = []
            for uid_str, weight in weights_data.items():
                uids.append(int(uid_str))
                weights.append(float(weight))

            uids = np.array(uids, dtype=np.int64)
            weights = np.array(weights, dtype=np.float32)

            timestamp = weight_set.get("timestamp", "unknown time")

            # Display this historical set
            display_weight_set(uids, weights, timestamp)

            # Check if this is a valid weight set
            if np.all(weights == 1.0):
                print("⚠️  All weights are 1.0 - This is likely a default/reset state")
                continue
            elif np.all(weights == 0.0):
                print("⚠️  All weights are 0.0 - This is likely a default/reset state")
                continue

            print("✅ Found valid weight set to use")
            return uids, weights

        raise Exception("No valid weight sets found (all were 1s or 0s)")

    except requests.exceptions.RequestException as e:
        raise Exception(f"Failed to fetch weights from Taostats: {str(e)}")


def verify_weights(uids: np.ndarray, weights: np.ndarray) -> bool:
    """Display weights and get user confirmation."""
    print("\nFinal weights to set on chain:")
    display_weight_set(uids, weights)

    while True:
        response = input(
            "\nDo you want to proceed with setting these weights? (y/n): "
        ).lower()
        if response in ["y", "n"]:
            return response == "y"
        print("Please enter 'y' or 'n'")


def set_weights_on_chain(
    wallet: "bt.wallet",
    subtensor: "bt.subtensor",
    netuid: int,
    uids: np.ndarray,
    weights: np.ndarray,
):
    """Set weights on chain using the provided wallet."""
    print("\nPreparing to set weights on chain...")

    # Convert weights and uids for chain emission
    uint_uids, uint_weights = bt.utils.weight_utils.convert_weights_and_uids_for_emit(
        uids=uids, weights=weights
    )

    print("Weights converted for chain emission")
    bt.logging.info(f"Setting weights: {uint_weights} for uids: {uint_uids}")

    # Get current spec version from subnet
    spec_version = subtensor.get_subnet_hyperparameters(netuid).weights_version
    print(f"Using subnet spec version: {spec_version}")

    # Set weights with proper parameters matching validator
    print("Sending weight setting transaction...")
    success, message = subtensor.set_weights(
        netuid=netuid,
        wallet=wallet,
        uids=uint_uids,
        weights=uint_weights,
        version_key=spec_version,
        wait_for_finalization=False,
        wait_for_inclusion=False,
        prompt=False,
    )

    if not success:
        raise Exception(f"Failed to set weights: {message}")


def parse_args():
    parser = argparse.ArgumentParser(
        description="Set weights from Taostats historical data"
    )
    parser.add_argument(
        "--netuid", type=int, default=42, help="Subnet UID (default: 42)"
    )
    parser.add_argument(
        "--wallet.name", type=str, default="default", help="Wallet name"
    )
    parser.add_argument(
        "--wallet.hotkey", type=str, default="default", help="Wallet hotkey name"
    )

    return parser.parse_args()


def main():
    args = parse_args()

    # Check for API key
    api_key = os.getenv("TAOSTATS_API_KEY")
    if not api_key:
        raise Exception("TAOSTATS_API_KEY environment variable not set")

    # Initialize bittensor objects
    print("\nInitializing bittensor...")
    subtensor = bt.subtensor(chain_endpoint="wss://entrypoint-finney.opentensor.ai:443")
    print(f"Connected to chain endpoint: {subtensor.chain_endpoint}")

    # Load wallet
    print("\nLoading wallet...")
    wallet = bt.wallet(name=args.wallet.name, hotkey=args.wallet.hotkey)
    if not wallet.is_registered():
        raise Exception("Wallet is not registered on chain")
    print(f"Using wallet: {wallet}")

    # Get weights from Taostats
    uids, weights = get_taostats_weights(wallet.hotkey.ss58_address, api_key)

    # Verify weights with user
    if not verify_weights(uids, weights):
        print("Operation cancelled by user")
        sys.exit(0)

    # Set weights on chain
    set_weights_on_chain(
        wallet, subtensor, netuid=args.netuid, uids=uids, weights=weights
    )
    print("✅ Successfully set weights on chain!")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"Error: {str(e)}", file=sys.stderr)
        sys.exit(1)

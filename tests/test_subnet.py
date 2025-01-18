import pytest
import bittensor as bt
from typing import Dict, List
import pandas as pd
from tabulate import tabulate


def analyze_subnet(netuid: int = 165, network: str = "test") -> Dict[str, List[Dict]]:
    """Analyze the subnet and return statistics for validators and miners."""
    subtensor = bt.subtensor(network=network)
    metagraph = subtensor.metagraph(netuid=netuid)

    validators = []
    miners = []

    # Collect all nodes
    for uid in range(len(metagraph.hotkeys)):
        axon = metagraph.axons[uid]
        stake = float(metagraph.S[uid])
        trust = float(metagraph.T[uid])
        consensus = float(metagraph.C[uid])
        incentive = float(metagraph.I[uid])
        dividends = float(metagraph.D[uid])
        emissions = float(metagraph.E[uid])
        is_active = bool(metagraph.active[uid])
        is_validator = bool(metagraph.validator_permit[uid])

        node_info = {
            "uid": uid,
            "hotkey": metagraph.hotkeys[uid],
            "ip": (
                f"{axon.ip}:{axon.port}"
                if axon.ip and axon.ip != "0.0.0.0"
                else "No IP"
            ),
            "stake": stake,
            "trust": trust,
            "consensus": consensus,
            "incentive": incentive,
            "dividends": dividends,
            "emissions": emissions,
            "active": is_active,
            "last_update": metagraph.last_update[uid],
            "validator_permit": is_validator,
        }

        if is_validator:
            validators.append(node_info)
        else:
            miners.append(node_info)

    return {"validators": validators, "miners": miners}


def print_node_stats(nodes: List[Dict], node_type: str):
    """Print statistics for a list of nodes in a nice table format."""
    if not nodes:
        print(f"\nNo {node_type}s found.")
        return

    # Convert to DataFrame for easy analysis
    df = pd.DataFrame(nodes)

    # Basic stats
    print(f"\n=== {node_type} Statistics ===")
    print(f"Total {node_type}s: {len(nodes)}")
    print(f"Active {node_type}s: {df['active'].sum()}")
    print(f"Total Stake: τ{df['stake'].sum():.2f}")
    print(f"Average Stake: τ{df['stake'].mean():.2f}")

    if node_type == "Validator":
        print(f"Average Trust: {df['trust'].mean():.4f}")
        print(f"Average Consensus: {df['consensus'].mean():.4f}")
    else:  # Miner
        print(f"Average Emissions: {df['emissions'].mean():.4f}")
        print(f"Total Emissions: {df['emissions'].sum():.4f}")

    # Sort nodes by stake and get top 10
    top_nodes = df.nlargest(10, "stake")

    print(f"\nTop 10 {node_type}s by Stake:")
    headers = ["UID", "Hotkey", "IP", "Stake", "Active"]
    if node_type == "Validator":
        headers.extend(["Trust", "Consensus"])
    else:
        headers.append("Emissions")

    table_data = []
    for _, node in top_nodes.iterrows():
        row = [
            node["uid"],
            node["hotkey"][:10] + "...",
            node["ip"],
            f"τ{node['stake']:.2f}",
            "✓" if node["active"] else "✗",
        ]
        if node_type == "Validator":
            row.extend([f"{node['trust']:.4f}", f"{node['consensus']:.4f}"])
        else:
            row.append(f"{node['emissions']:.4f}")
        table_data.append(row)

    print(tabulate(table_data, headers=headers, tablefmt="grid"))


def test_subnet_analysis():
    """Test to analyze and report on the current state of the subnet."""
    # Get subnet data
    subnet_data = analyze_subnet()

    # Print validator stats
    print_node_stats(subnet_data["validators"], "Validator")

    # Print miner stats
    print_node_stats(subnet_data["miners"], "Miner")

    # Basic assertions to ensure subnet is operational
    assert len(subnet_data["validators"]) > 0, "No validators found in subnet"
    assert len(subnet_data["miners"]) > 0, "No miners found in subnet"

    # Assert at least one validator is active
    assert any(
        v["active"] for v in subnet_data["validators"]
    ), "No active validators found"

    # Assert total stake is positive
    total_stake = sum(
        n["stake"] for n in subnet_data["validators"] + subnet_data["miners"]
    )
    assert total_stake > 0, "No stake found in subnet"

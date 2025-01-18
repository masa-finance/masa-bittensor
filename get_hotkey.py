import bittensor as bt

# Connect to test network and get metagraph
subtensor = bt.subtensor(network="test")
metagraph = subtensor.metagraph(netuid=165)

validators = []
miners = []

# Collect all nodes with real IPs
for uid in range(len(metagraph.hotkeys)):
    axon = metagraph.axons[uid]
    if axon.ip and axon.ip != "0.0.0.0":  # Has real IP
        stake = float(metagraph.S[uid])
        is_active = bool(metagraph.active[uid])
        is_validator = bool(metagraph.validator_permit[uid])
        trust = float(metagraph.T[uid])
        emissions = float(metagraph.E[uid])

        node_info = {
            "uid": uid,
            "hotkey": metagraph.hotkeys[uid],
            "ip": f"{axon.ip}:{axon.port}",
            "stake": stake,
            "active": is_active,
            "trust": trust,
            "emissions": emissions,
        }

        if is_validator:
            validators.append(node_info)
        else:
            miners.append(node_info)

# Sort validators by trust
validators.sort(key=lambda x: x["trust"], reverse=True)
print("\nTop Validators by Trust:")
for v in validators[:5]:  # Show top 5
    print(f"\nValidator (UID {v['uid']}):")
    print(f"Hotkey: {v['hotkey']}")
    print(f"IP: {v['ip']}")
    print(f"Stake: {v['stake']}")
    print(f"Active: {v['active']}")
    print(f"Trust: {v['trust']}")

# Sort miners by emissions
miners.sort(key=lambda x: x["emissions"], reverse=True)
print("\nTop Miners by Emissions:")
for m in miners[:5]:  # Show top 5
    print(f"\nMiner (UID {m['uid']}):")
    print(f"Hotkey: {m['hotkey']}")
    print(f"IP: {m['ip']}")
    print(f"Stake: {m['stake']}")
    print(f"Emissions: {m['emissions']}")

"""Configuration mappings for the project."""

# Mapping of mainnet subnet IDs to their corresponding testnet IDs
SUBNET_MAPPINGS = {
    # Mainnet -> Testnet
    "42": "165",  # Main AI subnet
    "59": "249",  # MASA subnet
}

# Mapping of network names to their chain endpoints
NETWORK_ENDPOINTS = {
    "test": "wss://test.finney.opentensor.ai:443",
    "main": "wss://entrypoint-finney.opentensor.ai:443",
}


def get_testnet_netuid(mainnet_netuid: str) -> str:
    """Get the testnet subnet ID for a given mainnet subnet ID."""
    return SUBNET_MAPPINGS.get(str(mainnet_netuid))


def get_mainnet_netuid(testnet_netuid: str) -> str:
    """Get the mainnet subnet ID for a given testnet subnet ID."""
    for mainnet, testnet in SUBNET_MAPPINGS.items():
        if testnet == str(testnet_netuid):
            return mainnet
    return None


def get_chain_endpoint(network: str) -> str:
    """Get the chain endpoint for a given network."""
    return NETWORK_ENDPOINTS.get(network)

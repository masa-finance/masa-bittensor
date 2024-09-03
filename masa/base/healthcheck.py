import typing
import requests
import bittensor as bt


class PingMiner(bt.Synapse):
    sent_from: typing.Optional[str]
    is_active: typing.Optional[bool]
    version: typing.Optional[int]

    def deserialize(self) -> str:
        return self.sent_from


def forward_ping(synapse: PingMiner, spec_version: int) -> PingMiner:
    synapse.is_active = True
    synapse.version = spec_version
    bt.logging.info(
        f"Validator requesting version: {synapse.sent_from}, Passing back: {synapse.version}"
    )

    return synapse


def get_external_ip() -> str:
    """
    Fetches the external IP address of the machine.

    Returns:
        str: The external IP address.
    """
    try:
        response = requests.get("https://api.ipify.org?format=json")
        response.raise_for_status()
        ip = response.json().get("ip")
        return ip
    except requests.RequestException as e:
        print(f"An error occurred while fetching the external IP: {e}")
        return None

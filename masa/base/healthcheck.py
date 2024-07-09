import typing
import bittensor as bt


class PingMiner(bt.Synapse):
    sent_from: typing.Optional[str]
    is_active: typing.Optional[bool]

    def deserialize(self) -> str:
        return self.sent_from


def forward_ping(synapse: PingMiner) -> PingMiner:
    synapse.is_active = True
    bt.logging.info(f"Got ping from {synapse.sent_from}")

    return synapse
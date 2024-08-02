import bittensor as bt

class MinerVersionRequest():
    def __init__(self):
        super().__init__()

    def get_version(self, miner) -> int:
        return miner.spec_version

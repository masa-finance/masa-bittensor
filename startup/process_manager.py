import os
import logging
import subprocess
from typing import List


class ProcessManager:
    """Manages the execution of validator and miner processes."""

    def __init__(self):
        """Initialize the process manager."""
        self.logger = logging.getLogger(__name__)

    def prepare_directories(self):
        """Prepare necessary directories for process execution."""
        state_path = os.path.expanduser("~/.bittensor/states")
        os.makedirs(state_path, mode=0o700, exist_ok=True)
        return state_path

    def build_validator_command(
        self,
        netuid: int,
        network: str,
        wallet_name: str,
        wallet_hotkey: str,
        axon_port: int,
        prometheus_port: int,
    ) -> List[str]:
        """Build the validator command with all necessary arguments.

        Args:
            netuid: Network UID
            network: Network name
            wallet_name: Name of the wallet
            wallet_hotkey: Hotkey name
            axon_port: Port for the validator's axon
            prometheus_port: Port for Prometheus metrics

        Returns:
            list: Command as a list of arguments
        """
        wallet_path = os.path.expanduser("~/.bittensor/wallets/")
        state_path = self.prepare_directories()

        return [
            "python",
            "neurons/validator.py",
            f"--netuid={netuid}",
            f"--subtensor.network={network}",
            f"--wallet.name={wallet_name}",
            f"--wallet.hotkey={wallet_hotkey}",
            f"--wallet.path={wallet_path}",
            f"--logging.logging_dir={state_path}",
            f"--axon.port={axon_port}",
            f"--prometheus.port={prometheus_port}",
            "--logging.debug",
        ]

    def build_miner_command(
        self,
        netuid: int,
        network: str,
        wallet_name: str,
        wallet_hotkey: str,
        axon_port: int,
        prometheus_port: int,
    ) -> List[str]:
        """Build the miner command with all necessary arguments.

        Args:
            netuid: Network UID
            network: Network name
            wallet_name: Name of the wallet
            wallet_hotkey: Hotkey name
            axon_port: Port for the miner's axon
            prometheus_port: Port for Prometheus metrics

        Returns:
            list: Command as a list of arguments
        """
        wallet_path = os.path.expanduser("~/.bittensor/wallets/")
        state_path = self.prepare_directories()

        return [
            "python",
            "neurons/miner.py",
            f"--netuid={netuid}",
            f"--subtensor.network={network}",
            f"--wallet.name={wallet_name}",
            f"--wallet.hotkey={wallet_hotkey}",
            f"--wallet.path={wallet_path}",
            f"--logging.logging_dir={state_path}",
            f"--axon.port={axon_port}",
            f"--prometheus.port={prometheus_port}",
            "--logging.debug",
            "--blacklist.force_validator_permit",
        ]

    def execute_validator(self, command: List[str]):
        """Execute the validator process.

        Args:
            command: Complete command as a list of arguments
        """
        self.logger.info(f"Executing validator command: {' '.join(command)}")
        # Use execvp to replace the current process
        os.execvp(command[0], command)

    def execute_miner(self, command: List[str]):
        """Execute the miner process.

        Args:
            command: Complete command as a list of arguments
        """
        self.logger.info(f"Executing miner command: {' '.join(command)}")
        # Use subprocess.run for miners
        subprocess.run(command)

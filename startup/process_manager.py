"""Process Manager Module.

This module handles the execution of validator and miner processes in the Agent Arena subnet.
It manages command building, directory preparation, and process execution.

Example:
    >>> manager = ProcessManager()
    >>> command = manager.build_validator_command(
    ...     netuid=249,
    ...     network="test",
    ...     wallet_name="subnet_249",
    ...     wallet_hotkey="validator_1",
    ...     logging_dir="/root/.bittensor/logs",
    ...     axon_port=8081,
    ...     prometheus_port=8082,
    ...     grafana_port=8083
    ... )
    >>> manager.execute_validator(command)
"""

import os
import logging
from typing import List


class ProcessManager:
    """Manages the execution of validator and miner processes.

    This class handles:
    - Directory preparation for logs and wallets
    - Command building for validators and miners
    - Process execution with proper arguments

    The manager ensures all necessary directories exist and have proper permissions
    before executing any processes.
    """

    def __init__(self):
        """Initialize the process manager with logging setup."""
        self.logger = logging.getLogger(__name__)

    def prepare_directories(self) -> str:
        """Prepare necessary directories for process execution.

        Creates required directories with proper permissions:
        - /root/.bittensor/logs: For process logs
        - /root/.bittensor/wallets: For wallet storage

        Returns:
            str: Base directory path (/root/.bittensor)
        """
        base_dir = "/root/.bittensor"
        os.makedirs(os.path.join(base_dir, "logs"), mode=0o700, exist_ok=True)
        os.makedirs(os.path.join(base_dir, "wallets"), mode=0o700, exist_ok=True)
        return base_dir

    def build_validator_command(
        self,
        netuid: int,
        network: str,
        wallet_name: str,
        wallet_hotkey: str,
        logging_dir: str,
        axon_port: int,
        prometheus_port: int,
        grafana_port: int,
    ) -> List[str]:
        """Build the validator command with all necessary arguments.

        Args:
            netuid: Network UID (249 for testnet, 59 for mainnet)
            network: Network name ("test" or "finney")
            wallet_name: Name of the wallet (format: "subnet_{netuid}")
            wallet_hotkey: Name of the hotkey (format: "validator_{replica}")
            logging_dir: Directory for logs
            axon_port: Port for the validator's axon server
            prometheus_port: Port for Prometheus metrics
            grafana_port: Port for Grafana dashboard

        Returns:
            List[str]: Complete command as a list of arguments

        Note:
            The command uses the run_validator.py script with appropriate flags
        """
        base_dir = self.prepare_directories()
        wallet_path = os.path.join(base_dir, "wallets")

        # Set environment for unbuffered output
        os.environ["PYTHONUNBUFFERED"] = "1"

        # Get logging levels from environment or use defaults
        log_level = os.getenv("LOG_LEVEL", "WARNING")
        console_level = os.getenv("CONSOLE_LOG_LEVEL", "WARNING")
        file_level = os.getenv("FILE_LOG_LEVEL", "INFO")

        command = [
            "python3",
            "-u",  # Force unbuffered output
            "scripts/run_validator.py",
            f"--netuid={netuid}",
            f"--wallet.name={wallet_name}",
            f"--wallet.hotkey={wallet_hotkey}",
            f"--wallet.path={wallet_path}",
            f"--logging.directory={os.path.join(base_dir, 'logs')}",
            f"--logging.logging_dir={os.path.join(base_dir, 'logs')}",
            f"--logging.level={log_level}",
            f"--logging.console_level={console_level}",
            f"--logging.file_level={file_level}",
            f"--axon.port={axon_port}",
            f"--prometheus.port={prometheus_port}",
            f"--grafana.port={grafana_port}",
        ]

        if network == "test":
            command.append("--subtensor.network=test")

        return command

    def build_miner_command(
        self,
        wallet_name: str,
        wallet_hotkey: str,
        netuid: int,
        network: str,
        logging_dir: str,
        axon_port: int,
        prometheus_port: int,
        grafana_port: int,
    ) -> List[str]:
        """Build the miner command with all necessary arguments.

        Args:
            wallet_name: Name of the wallet (format: "subnet_{netuid}")
            wallet_hotkey: Name of the hotkey (format: "miner_{replica}")
            netuid: Network UID (249 for testnet, 59 for mainnet)
            network: Network name ("test" or "finney")
            logging_dir: Directory for logs
            axon_port: Port for the miner's axon server
            prometheus_port: Port for Prometheus metrics
            grafana_port: Port for Grafana dashboard

        Returns:
            List[str]: Complete command as a list of arguments

        Note:
            The command uses the run_miner.py script with appropriate flags
        """
        base_dir = self.prepare_directories()
        wallet_path = os.path.join(base_dir, "wallets")

        # Set environment for unbuffered output and debug
        os.environ["PYTHONUNBUFFERED"] = "1"

        # Get logging levels from environment or use defaults
        log_level = os.getenv("LOG_LEVEL", "WARNING")
        console_level = os.getenv("CONSOLE_LOG_LEVEL", "WARNING")
        file_level = os.getenv("FILE_LOG_LEVEL", "INFO")

        command = [
            "python3",
            "-u",  # Force unbuffered output
            "scripts/run_miner.py",
            f"--netuid={netuid}",
            f"--wallet.name={wallet_name}",
            f"--wallet.hotkey={wallet_hotkey}",
            f"--wallet.path={wallet_path}",
            f"--logging.directory={os.path.join(base_dir, 'logs')}",
            f"--logging.logging_dir={os.path.join(base_dir, 'logs')}",
            f"--logging.level={log_level}",
            f"--logging.console_level={console_level}",
            f"--logging.file_level={file_level}",
            f"--axon.port={axon_port}",
            f"--prometheus.port={prometheus_port}",
            f"--grafana.port={grafana_port}",
        ]

        if network == "test":
            command.append("--subtensor.network=test")

        return command

    def execute_validator(self, command: List[str]) -> None:
        """Execute the validator process.

        Args:
            command: Complete command as a list of arguments

        Note:
            Uses os.execvp to replace the current process with the validator
            This means the process will not return unless there's an error
        """
        self.logger.info(f"Executing validator command: {' '.join(command)}")
        # Use execvp to replace the current process
        os.execvp(command[0], command)

    def execute_miner(self, command: List[str]) -> None:
        """Execute the miner process.

        Args:
            command: Complete command as a list of arguments

        Note:
            Uses os.execvp to replace the current process with the miner
            This means the process will not return unless there's an error
        """
        self.logger.info(f"Executing miner command: {' '.join(command)}")
        # Use execvp to replace the current process
        os.execvp(command[0], command)

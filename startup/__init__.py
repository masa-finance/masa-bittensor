"""Startup Module for Agent Arena Subnet.

This package handles container orchestration and initialization for the Masa Agent Arena subnet.
It provides functionality for wallet management, process execution, and service configuration.

Modules:
    wallet_manager: Handles wallet creation, loading, and registration
    process_manager: Manages service execution and command building
    report: Provides status reporting and logging utilities

Environment:
    Optional .env file at /app/.env with configuration overrides
    See .env.example for available variables

Example:
    To use this module:
    >>> from startup import WalletManager, ProcessManager
    >>> wallet_manager = WalletManager(role="validator", network="test", netuid=249)
    >>> process_manager = ProcessManager()
"""

import os
from pathlib import Path
from dotenv import load_dotenv
from startup.wallet_manager import WalletManager
from startup.process_manager import ProcessManager

# Load environment variables from .env file if it exists
env_path = Path("/app/.env")
if env_path.exists():
    load_dotenv(env_path)

__all__ = ["WalletManager", "ProcessManager"]

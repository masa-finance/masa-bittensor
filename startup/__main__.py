import os
import logging
from startup.wallet_manager import WalletManager
from startup.registration_manager import RegistrationManager
from startup.process_manager import ProcessManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def print_status_report(role, uid, hotkey, registered, network, port):
    """Print a formatted status report."""
    icon = "🔍" if role == "validator" else "⛏️ "
    role_title = role.capitalize()

    print(f"\n=== {icon} {role_title} Status Report ===\n")
    print("-" * 50)
    print(
        f"""
• {role_title} {uid or 'Unknown UID'}
  ├─ Network: {network}
  ├─ Status: {'✅ Running' if uid else '❌ Not Running'}
  ├─ Registration: {'✅ Registered' if registered else '❌ Not Registered'}
  ├─ Port: {port}
  └─ Hotkey: {hotkey or 'Unknown'}

Starting {role} process...
"""
    )


def main():
    # Print environment variables for debugging
    logger.info("=== PYTHON ENVIRONMENT VARIABLES ===")
    for key, value in sorted(os.environ.items()):
        logger.info(f"{key}={value}")
    logger.info("==================================")

    # Get role and replica number
    role = os.environ.get("ROLE", "unknown")
    replica_num = os.environ.get("REPLICA_NUM", "1")
    network = os.environ.get("NETWORK", "test")
    port = os.environ.get(f"{role.upper()}_PORT", "unknown")
    logger.info(f"Service: {role}, Replica: {replica_num}")

    # Initialize managers
    wallet_manager = WalletManager()
    registration_manager = RegistrationManager(wallet_manager)
    process_manager = ProcessManager()

    try:
        # Print status report
        print_status_report(
            role=role,
            uid=registration_manager.uid,
            hotkey=registration_manager.hotkey_ss58,
            registered=registration_manager.is_registered,
            network=network,
            port=port,
        )

        # Start the process
        process_manager.start()

    except Exception as e:
        logger.error(f"Error during startup: {str(e)}")
        raise


if __name__ == "__main__":
    main()

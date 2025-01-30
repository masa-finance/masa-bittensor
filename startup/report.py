import time
import logging
import subprocess

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_service_logs(service_name):
    """Get logs from a service using docker service logs."""
    try:
        cmd = f"docker service logs masa_{service_name}"
        result = subprocess.run(cmd.split(), capture_output=True, text=True)
        return result.stdout
    except Exception as e:
        logger.error(f"Error getting logs for {service_name}: {e}")
        return ""


def parse_logs(logs):
    """Parse logs for relevant information."""
    info = {
        "uid": None,
        "hotkey": None,
        "port": None,
        "status": "unknown",
        "registered": False,
    }

    for line in logs.split("\n"):
        if "Hotkey is registered with UID" in line:
            info["uid"] = line.split("UID")[-1].strip()
            info["registered"] = True
        elif "Hotkey address:" in line:
            info["hotkey"] = line.split("Hotkey address:")[-1].strip()
        elif "Running neuron on subnet:" in line:
            info["status"] = "running"

    return info


def generate_report():
    """Generate and display a startup report."""
    print("\n=== Masa Bittensor Startup Report ===\n")

    # Check validator logs
    validator_logs = get_service_logs("validator")
    validator_info = parse_logs(validator_logs)

    if validator_info["uid"] or validator_info["hotkey"]:
        print("🔍 Validator Status:")
        print("-" * 50)
        print(
            f"""
• Validator {validator_info['uid'] or 'Unknown UID'}
  ├─ Status: {'✅ Running' if validator_info['status'] == 'running' else '❌ Not Running'}
  ├─ Registration: {'✅ Registered' if validator_info['registered'] else '❌ Not Registered'}
  └─ Hotkey: {validator_info['hotkey'] or 'Unknown'}
"""
        )

    # Check miner logs
    miner_logs = get_service_logs("miner")
    miner_info = parse_logs(miner_logs)

    if miner_info["uid"] or miner_info["hotkey"]:
        print("\n⛏️  Miner Status:")
        print("-" * 50)
        print(
            f"""
• Miner {miner_info['uid'] or 'Unknown UID'}
  ├─ Status: {'✅ Running' if miner_info['status'] == 'running' else '❌ Not Running'}
  ├─ Registration: {'✅ Registered' if miner_info['registered'] else '❌ Not Registered'}
  └─ Hotkey: {miner_info['hotkey'] or 'Unknown'}
"""
        )

    print("\n✨ Startup Complete!")


if __name__ == "__main__":
    # Wait for services to initialize
    time.sleep(20)
    generate_report()

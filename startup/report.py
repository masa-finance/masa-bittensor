import time
import logging
import subprocess
import sys
from datetime import datetime

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


def get_service_status():
    """Get service status using docker service ls."""
    try:
        cmd = "docker service ls --format '{{.Name}} {{.Replicas}}'"
        result = subprocess.run(cmd.split(), capture_output=True, text=True, shell=True)
        return result.stdout
    except Exception as e:
        logger.error(f"Error getting service status: {e}")
        return ""


def parse_logs(logs):
    """Parse logs for relevant information."""
    info = {
        "uid": None,
        "hotkey": None,
        "port": None,
        "status": "unknown",
        "registered": False,
        "errors": [],
        "last_activity": None,
    }

    for line in logs.split("\n"):
        try:
            # Extract timestamp if present
            if ".masa_" in line and "] " in line:
                timestamp_str = line.split("] ")[0].split("[")[1]
                info["last_activity"] = datetime.strptime(
                    timestamp_str, "%Y-%m-%d %H:%M:%S.%f"
                )
        except (ValueError, IndexError):
            # Skip timestamp parsing errors
            pass

        if "Hotkey is registered with UID" in line:
            info["uid"] = line.split("UID")[-1].strip()
            info["registered"] = True
        elif "Hotkey address:" in line:
            info["hotkey"] = line.split("Hotkey address:")[-1].strip()
        elif "Running neuron on subnet:" in line:
            info["status"] = "running"
        elif "Error:" in line or "ERROR:" in line:
            info["errors"].append(line.strip())

    return info


def generate_report(wait_time=20):
    """Generate and display a startup report."""
    if wait_time > 0:
        print(f"\n⏳ Waiting {wait_time} seconds for services to initialize...\n")
        time.sleep(wait_time)

    print("\n=== 🌟 Masa Bittensor Startup Report ===\n")

    # Check service status first
    print("📊 Service Status:")
    print("-" * 50)
    service_status = get_service_status()
    for line in service_status.split("\n"):
        if "masa_" in line:
            name, replicas = line.strip().split()
            status = "✅" if replicas.startswith(replicas[0] + "/") else "⏳"
            print(f"{status} {name}: {replicas}")
    print()

    # Check validator logs
    validator_logs = get_service_logs("validator")
    validator_info = parse_logs(validator_logs)

    print("🔍 Validator Status:")
    print("-" * 50)
    print(
        f"""
• Validator {validator_info['uid'] or 'Unknown UID'}
  ├─ Status: {'✅ Running' if validator_info['status'] == 'running' else '⏳ Starting' if not validator_info['errors'] else '❌ Error'}
  ├─ Registration: {'✅ Registered' if validator_info['registered'] else '❌ Not Registered'}
  ├─ Hotkey: {validator_info['hotkey'] or 'Unknown'}
  └─ Last Activity: {validator_info['last_activity'].strftime('%H:%M:%S') if validator_info['last_activity'] else 'No activity'}
"""
    )

    if validator_info["errors"]:
        print("  ⚠️  Recent Errors:")
        for error in validator_info["errors"][-3:]:  # Show last 3 errors
            print(f"     • {error}")

    # Check miner logs
    miner_logs = get_service_logs("miner")
    miner_info = parse_logs(miner_logs)

    print("\n⛏️  Miner Status:")
    print("-" * 50)
    print(
        f"""
• Miner {miner_info['uid'] or 'Unknown UID'}
  ├─ Status: {'✅ Running' if miner_info['status'] == 'running' else '⏳ Starting' if not miner_info['errors'] else '❌ Error'}
  ├─ Registration: {'✅ Registered' if miner_info['registered'] else '❌ Not Registered'}
  ├─ Hotkey: {miner_info['hotkey'] or 'Unknown'}
  └─ Last Activity: {miner_info['last_activity'].strftime('%H:%M:%S') if miner_info['last_activity'] else 'No activity'}
"""
    )

    if miner_info["errors"]:
        print("  ⚠️  Recent Errors:")
        for error in miner_info["errors"][-3:]:  # Show last 3 errors
            print(f"     • {error}")

    print("\n📝 Summary:")
    print("-" * 50)
    all_running = all(
        info["status"] == "running" for info in [validator_info, miner_info]
    )
    all_registered = all(info["registered"] for info in [validator_info, miner_info])

    if all_running and all_registered:
        print("✅ All services are running and registered successfully!")
    else:
        print("⏳ Some services are still initializing or need attention.")
        print("\nTip: Run this report again in a few minutes to check progress.")
        print(
            "     You can also check detailed logs with: docker service logs masa_neuron -f"
        )


if __name__ == "__main__":
    # Allow custom wait time from command line
    wait_time = int(sys.argv[1]) if len(sys.argv) > 1 else 20
    generate_report(wait_time)

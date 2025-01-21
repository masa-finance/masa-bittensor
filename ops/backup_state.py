#!/usr/bin/env python3
import os
import glob
from datetime import datetime

STATE_FILE = (
    "/home/ubuntu/.bittensor/miners/validator/default/netuid42/validator/state.pt"
)
BACKUP_DIR = "/home/ubuntu/state_backups"
MAX_DAILY_BACKUPS = 2  # Keep 2 days of base backups
MAX_INCREMENTAL = 24  # Keep 24 hourly incremental backups per day


def get_state_name():
    """Get the base name of the state file without path"""
    return os.path.basename(STATE_FILE)


def get_latest_base():
    """Get the most recent base backup file"""
    base_backups = glob.glob(os.path.join(BACKUP_DIR, f"{get_state_name()}.base.*"))
    return max(base_backups, key=os.path.getmtime) if base_backups else None


def create_base_backup():
    """Create a new daily base backup"""
    timestamp = datetime.now().strftime("%Y%m%d")
    base_path = os.path.join(BACKUP_DIR, f"{get_state_name()}.base.{timestamp}")

    try:
        # Create new base backup
        os.system(f"cp {STATE_FILE} {base_path}")
        print(f"Created base backup: {base_path}")

        # Clean old base backups
        base_backups = glob.glob(os.path.join(BACKUP_DIR, f"{get_state_name()}.base.*"))
        base_backups.sort(key=os.path.getmtime)
        while len(base_backups) > MAX_DAILY_BACKUPS:
            old_backup = base_backups.pop(0)
            # Also remove associated incremental backups
            incremental = glob.glob(f"{old_backup}.inc.*")
            for inc in incremental:
                os.remove(inc)
                print(f"Removed incremental backup: {inc}")
            os.remove(old_backup)
            print(f"Removed old base backup: {old_backup}")

        return base_path
    except Exception as e:
        print(f"Error creating base backup: {e}")
        return None


def create_incremental_backup():
    """Create an incremental backup based on the latest base"""
    base_backup = get_latest_base()
    if not base_backup:
        base_backup = create_base_backup()
        if not base_backup:
            print("Failed to create base backup")
            return

    # Get base name without any .inc extensions
    base_name = base_backup.split(".inc.")[0]
    timestamp = datetime.now().strftime("%H%M%S")
    diff_path = f"{base_name}.inc.{timestamp}"

    try:
        # Create binary diff between current state and base using xdelta3
        result = os.system(f"xdelta3 -e -s {base_backup} {STATE_FILE} {diff_path}")
        if result != 0:
            print("Error creating binary diff")
            if os.path.exists(diff_path):
                os.remove(diff_path)
            return

        if os.path.getsize(diff_path) == 0:
            os.remove(diff_path)
            print("No changes detected, skipping incremental backup")
            return

        print(f"Created incremental backup: {diff_path}")

        # Clean old incremental backups for this base
        incremental = glob.glob(f"{base_name}.inc.*")
        incremental.sort(key=os.path.getmtime)
        while len(incremental) > MAX_INCREMENTAL:
            old_inc = incremental.pop(0)
            os.remove(old_inc)
            print(f"Removed old incremental backup: {old_inc}")

    except Exception as e:
        print(f"Error creating incremental backup: {e}")


def create_backup():
    """Main backup function"""
    # Ensure backup directory exists
    os.makedirs(BACKUP_DIR, exist_ok=True)

    # Check if we need a new base backup (daily)
    latest_base = get_latest_base()
    if (
        not latest_base
        or datetime.fromtimestamp(os.path.getmtime(latest_base)).date()
        < datetime.now().date()
    ):
        create_base_backup()
    else:
        create_incremental_backup()


if __name__ == "__main__":
    create_backup()

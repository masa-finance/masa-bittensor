#!/usr/bin/env python3
import torch
import os


def test_load(file_path):
    print(f"\nTesting file: {file_path}")
    try:
        state = torch.load(file_path)
        print("✓ Successfully loaded state")
        print(f"State contains {len(state)} items")
        return True
    except Exception as e:
        print(f"✗ Failed to load state: {e}")
        return False


if __name__ == "__main__":
    backup_dir = "/home/ubuntu/state_backups"

    # Test base backup
    base_files = [f for f in os.listdir(backup_dir) if f.endswith(".base.20250121")]
    for f in base_files:
        test_load(os.path.join(backup_dir, f))

    # Test incremental backups
    inc_files = [f for f in os.listdir(backup_dir) if ".inc." in f]
    for f in inc_files:
        test_load(os.path.join(backup_dir, f))

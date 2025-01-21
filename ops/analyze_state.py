#!/usr/bin/env python3
import torch


def analyze_state(file_path):
    print(f"\nAnalyzing state file: {file_path}")
    state = torch.load(file_path)

    print("\nTop level keys:", state.keys())

    for key, value in state.items():
        print(f"\nKey: {key}")
        if isinstance(value, dict):
            print("Type: dict")
            print("Nested keys:", value.keys())
            for k, v in value.items():
                print(f"  {k}: {type(v)}")
                if hasattr(v, "shape"):
                    print(f"    Shape: {v.shape}")
                elif hasattr(v, "__len__"):
                    print(f"    Length: {len(v)}")
        elif isinstance(value, (list, tuple)):
            print("Type:", type(value))
            print("Length:", len(value))
            if len(value) > 0:
                print("First element type:", type(value[0]))
        else:
            print("Type:", type(value))
            if hasattr(value, "shape"):
                print("Shape:", value.shape)
            elif hasattr(value, "__len__"):
                print("Length:", len(value))


if __name__ == "__main__":
    state_file = (
        "/home/ubuntu/.bittensor/miners/validator/default/netuid42/validator/state.pt"
    )
    analyze_state(state_file)

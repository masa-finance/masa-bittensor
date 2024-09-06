#!/bin/bash

command_to_run="btcli subnet register --netuid 42 --wallet.name miner --wallet.hotkey fourth --subtensor.network finney --no_prompt"
eval "$command_to_run"
########################################################################
#####                    NETWORK CONFIGURATION                      #####
########################################################################

# Default to mainnet if not specified
NETWORK ?= main

# Network-specific configurations
ifeq ($(NETWORK),test)
    SUBTENSOR_CHAIN = network test
    NETUID = 165
else ifeq ($(NETWORK),main)
    SUBTENSOR_CHAIN = network finney 
#    SUBTENSOR_CHAIN = network wss://entrypoint-finney.masa.ai
    NETUID = 42
else
    $(error Invalid network specified. Use NETWORK=test or NETWORK=main)
endif

########################################################################
#####                       USEFUL COMMANDS                        #####
########################################################################

list-wallets:
	btcli wallet list

overview-all:
	btcli wallet overview --all --subtensor.$(SUBTENSOR_CHAIN)

balance-all:
	btcli wallet balance --all --subtensor.$(SUBTENSOR_CHAIN)

list-subnets:
	btcli subnets list --subtensor.$(SUBTENSOR_CHAIN)

register-miner:
	btcli subnet register --wallet.name miner --wallet.hotkey default --subtensor.$(SUBTENSOR_CHAIN) --netuid $(NETUID)

register-validator:
	btcli subnet register --wallet.name validator --wallet.hotkey default --subtensor.$(SUBTENSOR_CHAIN) --netuid $(NETUID)

register-validator-root:
	btcli root register --wallet.name validator --wallet.hotkey default --subtensor.$(SUBTENSOR_CHAIN)

stake-validator:
	btcli stake add --wallet.name validator --wallet.hotkey default --subtensor.$(SUBTENSOR_CHAIN) --netuid $(NETUID)

boost-root:
	btcli root boost --netuid $(NETUID) --increase 1 --wallet.name validator --wallet.hotkey default --subtensor.$(SUBTENSOR_CHAIN)

set-weights:
	btcli root weights --subtensor.$(SUBTENSOR_CHAIN)

run-miner:
	@echo "Running miner on $(NETWORK)net (netuid: $(NETUID))"
	python neurons/miner.py --netuid $(NETUID) --subtensor.$(SUBTENSOR_CHAIN) --wallet.name miner --wallet.hotkey default --axon.port 8091 --neuron.debug --logging.debug --blacklist.force_validator_permit

run-validator:
	@echo "Running validator on $(NETWORK)net (netuid: $(NETUID))"
	python neurons/validator.py --netuid $(NETUID) --subtensor.$(SUBTENSOR_CHAIN) --wallet.name validator --wallet.hotkey default --axon.port 8092 --neuron.info --logging.info --neuron.axon_off

hyperparameters:
	btcli subnets hyperparameters --subtensor.$(SUBTENSOR_CHAIN) --netuid $(NETUID)

metagraph:
	btcli subnets metagraph --subtensor.$(SUBTENSOR_CHAIN) --netuid $(NETUID)

test-miner:
	pytest -s -p no:warnings tests/test_miner.py

test-validator:
	pytest -s -p no:warnings tests/test_validator.py

test-all:
	pytest -s -p no:warnings tests/test_miner.py tests/test_validator.py

.PHONY: help
help:
	@echo "Usage:"
	@echo "  make <command> NETWORK=<network>"
	@echo ""
	@echo "Networks:"
	@echo "  main    Mainnet (default)"
	@echo "  test    Testnet"
	@echo ""
	@echo "Commands:"
	@echo "  run-validator    Run validator node"
	@echo "  run-miner       Run miner node"
	@echo "  list-wallets    List all wallets"
	@echo "  overview-all    Show overview of all wallets"
	@echo "  balance-all     Show balance of all wallets"
	@echo "  list-subnets    List all subnets"
	@echo "  and more..."

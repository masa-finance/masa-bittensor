TESTNET = network test
MAINNET = network finney

########################################################################
#####                       SELECT YOUR ENV                        #####
########################################################################

# SUBTENSOR_ENVIRONMENT = $(TESTNET)
SUBTENSOR_ENVIRONMENT = $(MAINNET)

# NETUID = 165 # testnet
NETUID = 42 # mainnet

########################################################################
#####                       USEFUL COMMANDS                        #####
########################################################################

list-wallets:
	btcli wallet list

overview-all:
	btcli wallet overview --all --subtensor.$(SUBTENSOR_ENVIRONMENT)

balance-all:
	btcli wallet balance --all --subtensor.$(SUBTENSOR_ENVIRONMENT)

list-subnets:
	btcli subnets list --subtensor.$(SUBTENSOR_ENVIRONMENT)

register-miner:
	btcli subnet register --wallet.name miner --wallet.hotkey default --subtensor.$(SUBTENSOR_ENVIRONMENT) --netuid $(NETUID)

register-validator:
	btcli subnet register --wallet.name validator --wallet.hotkey default --subtensor.$(SUBTENSOR_ENVIRONMENT) --netuid $(NETUID)

register-validator-root:
	btcli root register --wallet.name validator --wallet.hotkey default --subtensor.$(SUBTENSOR_ENVIRONMENT)

stake-validator:
	btcli stake add --wallet.name validator --wallet.hotkey default --subtensor.$(SUBTENSOR_ENVIRONMENT) --netuid $(NETUID)

boost-root:
	btcli root boost --netuid $(NETUID) --increase 1 --wallet.name validator --wallet.hotkey default --subtensor.$(SUBTENSOR_ENVIRONMENT)

set-weights:
	btcli root weights --subtensor.$(SUBTENSOR_ENVIRONMENT)

run-miner:
	python neurons/miner.py --netuid $(NETUID) --subtensor.$(SUBTENSOR_ENVIRONMENT) --wallet.name miner --wallet.hotkey default --axon.port 8091 --neuron.debug --logging.debug --logging.logging_dir ~/.bittensor/wallets --blacklist.force_validator_permit

run-validator:
	python neurons/validator.py --netuid $(NETUID) --subtensor.$(SUBTENSOR_ENVIRONMENT) --wallet.name validator --wallet.hotkey default --axon.port 8092 --neuron.debug --logging.debug --logging.logging_dir ~/.bittensor/wallets --neuron.axon_off

hyperparameters:
	btcli subnets hyperparameters --subtensor.$(SUBTENSOR_ENVIRONMENT) --netuid $(NETUID)

metagraph:
	btcli subnets metagraph --subtensor.$(SUBTENSOR_ENVIRONMENT) --netuid $(NETUID)

test-miner:
	pytest -s -p no:warnings tests/test_miner.py

test-validator:
	pytest -s -p no:warnings tests/test_validator.py

test-all:
	pytest -s -p no:warnings tests/test_miner.py tests/test_validator.py


LOCAL_ENDPOINT = ws://127.0.0.1:9945
LOCAL_ENVIRONMENT = chain_endpoint $(LOCAL_ENDPOINT)

# AWS_ENDPOINT = ws://54.144.144.227:9945 # DEV
AWS_ENDPOINT = ws://54.157.190.36:9945 # MAIN
AWS_ENVIRONMENT = chain_endpoint $(AWS_ENDPOINT)

TEST_ENVIRONMENT = network test

BITTENSOR_PATH=/Users/juam/Projects/masa-finance/bittensor/bittensor-1
NETUID = 1
# NETUID = 165 # Testnet subnet created by Mati


########################################################################
#####                       SELECT YOUR ENV                        #####
########################################################################
# ENVIRONMENT = $(LOCAL_ENVIRONMENT)
ENVIRONMENT = $(AWS_ENVIRONMENT)
# ENVIRONMENT = $(TEST_ENVIRONMENT)


########################################################################
#####                       USEFUL COMMANDS                        #####
########################################################################

## Wallet funding
fund-owner-wallet:
	btcli wallet faucet --wallet.name owner --subtensor.$(ENVIRONMENT)

fund-validator-wallet:
	btcli wallet faucet --wallet.name validator --subtensor.$(ENVIRONMENT)

fund-miner-wallet:
	btcli wallet faucet --wallet.name miner --subtensor.$(ENVIRONMENT)

## Subnet creation
create-subnet:
	btcli subnet create --wallet.name owner --subtensor.$(ENVIRONMENT)

## Subnet and wallet info
overview-all:
	btcli wallet overview --all --subtensor.$(ENVIRONMENT)

balance-all:
	btcli wallet balance --all --subtensor.$(ENVIRONMENT)

list-subnets:
	btcli subnets list --subtensor.$(ENVIRONMENT)

## Validator setup
stake-validator:
	btcli stake add --wallet.name validator --wallet.hotkey default --subtensor.$(ENVIRONMENT)

register-validator:
	btcli subnet register --wallet.name validator --wallet.hotkey default --subtensor.$(ENVIRONMENT)

register-validator-root:
	btcli root register --wallet.name validator --wallet.hotkey default --subtensor.$(ENVIRONMENT)

## Register miner + Key Registration Validation
register-miner:
	btcli subnet register --wallet.name miner --wallet.hotkey default --subtensor.$(ENVIRONMENT)

validate-key-registration:
	btcli subnet list --subtensor.$(ENVIRONMENT)

## Setup weights
boost-root:
	btcli root boost --netuid $(NETUID) --increase 1 --wallet.name validator --wallet.hotkey default --subtensor.$(ENVIRONMENT)

set-weights:
	btcli root weights --subtensor.$(ENVIRONMENT)

## Run miner and validator
run-miner:
	python neurons/miner.py --netuid $(NETUID) --subtensor.$(ENVIRONMENT) --wallet.name miner --wallet.hotkey default --logging.debug

run-validator:
	python neurons/validator.py --netuid $(NETUID) --subtensor.$(ENVIRONMENT) --wallet.name validator --wallet.hotkey default --logging.debug

## Docker commands
docker-build:
	docker build -f Dockerfile.masa -t masa-subtensor .

docker-run:
	docker run -d --name masa-subtensor -p 30333:30333 -p 9933:9933 -p 9944:9944 -p 9945:9945 -p 9946:9946 masa-subtensor

docker-run-remote:
	docker run -d --name masa-subtensor -p 30333:30333 -p 9933:9933 -p 9944:9944 -p 9945:9945 -p 9946:9946 ghcr.io/masa-finance/subtensor:arm-latest

########################################################################
########################################################################


## Helpful commands (generally don't run well on their own with Makefiles)
## because each line in recipe runs on its own shell invocation
activate-environment:
	conda activate bittensor
bittensor-path-export:
	export PYTHONPATH=$(BITTENSOR_PATH)
########################################################################

## Subtensor repo related commands (not needed here)
build-binary:
	cargo build --release --features pow-faucet

run-localnet:
	BUILD_BINARY=0 ./scripts/localnet.sh
########################################################################
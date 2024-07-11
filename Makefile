BRANCH_NAME := $(shell git rev-parse --abbrev-ref HEAD)
DOCKER_COMPOSE := BRANCH_NAME=$(BRANCH_NAME) docker compose

LOCAL_ENDPOINT = ws://127.0.0.1:9945
LOCALNET = chain_endpoint $(LOCAL_ENDPOINT)

DEVNET_ENDPOINT = ws://54.205.45.3:9945
DEVNET = chain_endpoint $(DEVNET_ENDPOINT)

INCENTIVIZED_TESTNET_ENDPOINT = ws://100.28.51.29:9945
INCENTIVIZED_TESTNET = chain_endpoint $(INCENTIVIZED_TESTNET_ENDPOINT)

TESTNET = network test

NETUID = 1 # devnet
# NETUID = 165 # testnet


########################################################################
#####                       SELECT YOUR ENV                        #####
########################################################################
# SUBTENSOR_ENVIRONMENT = $(LOCALNET)
SUBTENSOR_ENVIRONMENT = $(INCENTIVIZED_TESTNET)
# SUBTENSOR_ENVIRONMENT = $(DEVNET)
# SUBTENSOR_ENVIRONMENT = $(TESTNET)


########################################################################
#####                       USEFUL COMMANDS                        #####
########################################################################

## Wallet funding
fund-owner-wallet:
	btcli wallet faucet --wallet.name owner --subtensor.$(SUBTENSOR_ENVIRONMENT)

fund-validator-wallet:
	btcli wallet faucet --wallet.name validator --subtensor.$(SUBTENSOR_ENVIRONMENT)

fund-miner-wallet:
	btcli wallet faucet --wallet.name miner --subtensor.$(SUBTENSOR_ENVIRONMENT)

## Subnet creation
create-subnet:
	btcli subnet create --wallet.name owner --subtensor.$(SUBTENSOR_ENVIRONMENT)

## Subnet and wallet info
list-wallets:
	btcli wallet list

overview-all:
	btcli wallet overview --all --subtensor.$(SUBTENSOR_ENVIRONMENT)

balance-all:
	btcli wallet balance --all --subtensor.$(SUBTENSOR_ENVIRONMENT)

list-subnets:
	btcli subnets list --subtensor.$(SUBTENSOR_ENVIRONMENT)

## Validator setup
stake-validator:
	btcli stake add --wallet.name validator --wallet.hotkey default --subtensor.$(SUBTENSOR_ENVIRONMENT)

register-validator:
	btcli subnet register --wallet.name validator --wallet.hotkey default --subtensor.$(SUBTENSOR_ENVIRONMENT)

register-validator-root:
	btcli root register --wallet.name validator --wallet.hotkey default --subtensor.$(SUBTENSOR_ENVIRONMENT)

## Register miner + Key Registration Validation
register-miner:
	btcli subnet register --wallet.name miner --wallet.hotkey default --subtensor.$(SUBTENSOR_ENVIRONMENT)

validate-key-registration:
	btcli subnet list --subtensor.$(SUBTENSOR_ENVIRONMENT)

## Setup weights
boost-root:
	btcli root boost --netuid $(NETUID) --increase 1 --wallet.name validator --wallet.hotkey default --subtensor.$(SUBTENSOR_ENVIRONMENT)

set-weights:
	btcli root weights --subtensor.$(SUBTENSOR_ENVIRONMENT)

## Run miner and validator
run-miner:
	watchfiles "python neurons/miner.py --blacklist.force_validator_permit --netuid $(NETUID) --subtensor.$(SUBTENSOR_ENVIRONMENT) --wallet.name miner --wallet.hotkey default --axon.port 8091 --neuron.debug --logging.debug" .

run-validator:
	watchfiles "python neurons/validator.py --netuid $(NETUID) --subtensor.$(SUBTENSOR_ENVIRONMENT) --wallet.name validator --wallet.hotkey default --axon.port 8092 --neuron.debug --logging.debug" .

## Docker commands
docker-build:
	docker build -f Dockerfile.masa -t masa-subtensor .

docker-run:
	docker run -d --name masa-subtensor -p 30333:30333 -p 9933:9933 -p 9944:9944 -p 9945:9945 -p 9946:9946 masa-subtensor

docker-run-remote:
	docker run -d --name masa-subtensor -p 30333:30333 -p 9933:9933 -p 9944:9944 -p 9945:9945 -p 9946:9946 ghcr.io/masa-finance/subtensor:arm-latest


########################################################################
#####                       VALIDATOR API                          #####
########################################################################

test-profile:
	curl -X GET "http://localhost:8000/data/twitter/brendanplayford" -H "Authorization: Bearer 1234"

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

## Hyperparameters and metagraph
hyperparameters:
	btcli subnets hyperparameters --subtensor.$(SUBTENSOR_ENVIRONMENT) --netuid $(NETUID)

metagraph:
	btcli subnets metagraph --subtensor.$(SUBTENSOR_ENVIRONMENT) --netuid $(NETUID)

########################################################################
#####                   DOCKER COMPOSE COMMANDS                    #####
########################################################################

.PHONY: up down build logs

pull:
	$(DOCKER_COMPOSE) pull

up:
	$(DOCKER_COMPOSE) up -d --pull always

down:
	$(DOCKER_COMPOSE) down

build:
	$(DOCKER_COMPOSE) build

logs:
	$(DOCKER_COMPOSE) logs -f

# You can keep your existing docker commands or replace them with these:
docker-build:
	$(DOCKER_COMPOSE) build

docker-up:
	$(DOCKER_COMPOSE) up -d --pull always

docker-down:
	$(DOCKER_COMPOSE) down
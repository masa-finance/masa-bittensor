# Hyperparameters

Hyperparameters are used to define various settings on a subnet. To view our research on the topic, see the [research](https://github.com/masa-finance/masa-bittensor/issues/61).

You must be the owner of a given subnet to set its hyperparameters.

To view the hyperparameters for a given subnet, make sure the `Makefile` has the correct `SUBTENSOR_ENVIRONMENT` and `NETUID`, then run:

```bash
make hyperparameters
```

## Devnet Setup

Our devnet environment currently requires just one hyperparameter to be set that differs from the default configuration. We update `weights_rate_limit` from `100` to `5`, to make it quicker for new users to onboard to the subnet.

1.  Set `weights_rate_limit` to `5`

```bash
btcli sudo set --param weights_rate_limit --value 5 --netuid 1 --subtensor.chain_endpoint ws://54.205.45.3:9945
```

## Testnet Setup

- coming soon

## Mainnet Setup

- coming soon

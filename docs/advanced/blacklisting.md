# Blacklisting

## VPermit Filter

Current blacklisting logic is implemented by passing a flag to the miner:

```bash
python neurons/miner.py --blacklist.force_validator_permit
```

The above toggles the blacklisting logic, which is currently configured to filter out requests from neuron uid's that do _not_ have a valid permit.

```python
[blacklisted, reason] = await self.blacklist(synapse)
if blacklisted:
    bt.logging.warning(f"Blacklisting un-registered hotkey for reason: {reason}")
    return synapse
```

The blacklisting function extends that of the subnet-template:

```python
async def blacklist(self, synapse: Request) -> typing.Tuple[bool, str]:

    if await self.check_tempo():
        await self.check_stake(synapse)

    hotkey = synapse.dendrite.hotkey
    uid = self.metagraph.hotkeys.index(hotkey)

    bt.logging.info(f"Neurons Staked: {self.neurons_permit_stake}")
    bt.logging.info(f"Validator Permit: {self.metagraph.validator_permit[uid]}")

    if not self.config.blacklist.allow_non_registered and hotkey not in self.metagraph.hotkeys:
        bt.logging.warning(f"Blacklisting un-registered hotkey {hotkey}")
        return True, "Unrecognized hotkey"
    if self.config.blacklist.force_validator_permit and not self.metagraph.validator_permit[uid]:
        bt.logging.warning(f"Blacklisting a request from non-validator hotkey {hotkey}")
        return True, "Non-validator hotkey"
    if hotkey not in self.neurons_permit_stake:
        bt.logging.warning(f"Blacklisting a request from neuron without enough staked: {hotkey}")
        return True, "Non-staked neuron"

    bt.logging.info(f"Not Blacklisting recognized hotkey {hotkey}")
    return False, "Hotkey recognized!"
```

A check for a certain amount of stake is added to the blacklisting function, updating every tempo. This creates the requirement that a neuron must have staked for at least the tempo amount of blocks to be considered valid. This prevents spam and ensures that the network is not overwhelmed by new neurons. Now, with the presence of both a `vpermit` and having your `hotkey` listed on the permit_stake whitelist, you are considered a validator.

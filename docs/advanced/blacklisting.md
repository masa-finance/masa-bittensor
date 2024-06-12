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

The blacklisting function mimics that of the subnet-template:

```python
async def blacklist(self, synapse: Request) -> typing.Tuple[bool, str]:
    uid = self.metagraph.hotkeys.index(synapse.dendrite.hotkey)
    bt.logging.info(f"Validator Permit: {self.metagraph.validator_permit[uid]}")
    if not self.config.blacklist.allow_non_registered and synapse.dendrite.hotkey not in self.metagraph.hotkeys:
        bt.logging.warning(f"Blacklisting un-registered hotkey {synapse.dendrite.hotkey}")
        return True, "Unrecognized hotkey"
    if self.config.blacklist.force_validator_permit and not self.metagraph.validator_permit[uid]:
        bt.logging.warning(f"Blacklisting a request from non-validator hotkey {synapse.dendrite.hotkey}")
        return True, "Non-validator hotkey"
    bt.logging.info(f"Not Blacklisting recognized hotkey {synapse.dendrite.hotkey}")
    return False, "Hotkey recognized!"
```

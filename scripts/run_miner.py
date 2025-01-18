import asyncio
from neurons.miner_neuron import MasaMiner


async def main():
    # Initialize miner
    miner = MasaMiner()
    await miner.start()

    # Keyboard handler
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        await miner.stop()


if __name__ == "__main__":
    asyncio.run(main())

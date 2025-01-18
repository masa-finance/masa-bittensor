import asyncio
from neurons.validator_neuron import MasaValidator


async def main():
    # Initialize validator
    validator = MasaValidator()
    await validator.start()

    # Keyboard handler
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        await validator.stop()


if __name__ == "__main__":
    asyncio.run(main())

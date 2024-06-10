from masa.types.discord import DiscordProfileObject

def discord_parser(discord_responses):
    return [
        [DiscordProfileObject(**item) for item in response]
        for response in discord_responses  # Each response is a list of dictionaries
    ]

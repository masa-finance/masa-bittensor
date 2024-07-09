from masa.types.discord import DiscordGuildObject


def all_guilds_parser(all_guilds_responses):
    return [
        [DiscordGuildObject(**guild) for guild in response]
        for response in all_guilds_responses  # Each response is a list of dictionaries
    ]

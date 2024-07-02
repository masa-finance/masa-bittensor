from masa.types.discord import DiscordGuildChannelObject


def all_guilds_parser(all_guilds_responses):
    return [
        DiscordGuildChannelObject(**guild)
        for response in all_guilds_responses  # Each response is a list of dictionaries
        for guild in response
    ]

from masa.types.discord import DiscordGuildChannelObject


def guild_channels_parser(guild_channels_responses):
    return [
        [DiscordGuildChannelObject(**guild_channel) for guild_channel in response]
        for response in guild_channels_responses  # Each response is a list of dictionaries
    ]

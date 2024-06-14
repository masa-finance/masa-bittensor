from masa.types.discord import DiscordChannelMessageObject

def guild_channels_parser(guild_channels_responses):
    return [
        [DiscordChannelMessageObject(**guild_channel) for guild_channel in response]
        for response in guild_channels_responses  # Each response is a list of dictionaries
    ]
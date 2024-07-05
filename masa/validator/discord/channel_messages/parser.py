from masa.types.discord import DiscordChannelMessageObject


def channel_messages_parser(channel_messages_responses):
    return [
        [DiscordChannelMessageObject(**channel_message) for channel_message in response]
        for response in channel_messages_responses  # Each response is a list of dictionaries
    ]

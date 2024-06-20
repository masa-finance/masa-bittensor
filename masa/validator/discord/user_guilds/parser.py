from masa.types.discord import DiscordGuildObject

def user_guilds_parser(user_guilds_responses):
    return [
        DiscordGuildObject(**user_guild) 
        for response in user_guilds_responses  # Each response is a list of dictionaries
        for user_guild in response
    ]
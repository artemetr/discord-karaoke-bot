import os

from src.karaoke_bot import Karaoke, KaraokeBotConfig

Karaoke(KaraokeBotConfig(guild_id=952993401836556379)) \
    .run(os.getenv('DISCORD_TOKEN'))
